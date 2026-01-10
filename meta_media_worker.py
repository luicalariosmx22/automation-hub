"""
Worker durable para procesar descargas de media desde webhooks Meta.

Procesa eventos PENDING de forma robusta con:
- Retry con backoff exponencial
- Logging detallado de errores
- Persistencia de URLs públicas en Supabase Storage
- Idempotencia (no reprocesa si ya existe media)

Uso:
    python scripts/run_meta_media_worker.py
"""

import time
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clientes.aura import create_app
from clientes.aura.utils.supabase_client import supabase
from clientes.aura.utils.meta_webhook_helper_ingest import procesar_eventos_pendientes, procesar_ultimos_eventos
from clientes.aura.utils.meta_webhook_helpers import descargar_imagen_publicacion
from clientes.aura.routes.panel_cliente_meta_ads.webhooks_meta import obtener_token_apropiado
import requests
import os
from pathlib import Path
import mimetypes

logger = logging.getLogger(__name__)

# Configuración de backoff exponencial (segundos)
RETRY_DELAYS = [15, 60, 300, 1800, 7200]  # 15s, 1m, 5m, 30m, 2h
MAX_ATTEMPTS = len(RETRY_DELAYS)
BATCH_SIZE = 50
POLL_INTERVAL = 10  # segundos



def descargar_media_desde_url(url: str, post_id: str, nombre_nora: str, tipo: str) -> dict:
    """
    Descarga media directamente desde URL de Facebook y guarda en Supabase Storage.

    Args:
        url: URL de la imagen/video en Facebook
        post_id: ID del post (para nombrar archivo)
        nombre_nora: Tenant
        tipo: 'photo' o 'video'

    Returns:
        dict: {'success': bool, 'url_public': str, 'error': str}
    """
    try:
        # Descargar archivo
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Determinar extensión
        content_type = response.headers.get('content-type', '')
        ext = mimetypes.guess_extension(content_type) or '.jpg'

        # Nombre de archivo
        filename = f"{post_id.replace('/', '_')}{ext}"

        # Path en storage
        storage_path = f"{nombre_nora}/publicaciones_meta/{filename}"

        # Subir a Supabase Storage
        try:
            supabase.storage.from_('meta-webhooks').upload(
                path=storage_path,
                file=response.content,
                file_options={"content-type": content_type, "upsert": "true"}
            )
        except Exception as upload_err:
            # Si ya existe (409), no es error
            if '409' in str(upload_err) or 'already exists' in str(upload_err).lower():
                logger.info(f"⚠️ Archivo ya existe en storage: {storage_path}")
            else:
                raise

        # Obtener URL pública
        url_public = supabase.storage.from_('meta-webhooks').get_public_url(storage_path)

        # Actualizar meta_publicaciones_webhook (guardar URL pública y ruta física)
        if tipo == 'video':
            updates = {
                'video_local': url_public,
                'video_url_public': url_public,
                'video_storage_path': storage_path,
                'video_descargado_en': datetime.utcnow().isoformat()
            }
        else:
            updates = {
                'imagen_local': url_public,
                'thumbnail_url_public': url_public,
                'thumbnail_storage_path': storage_path,
                'imagen_descargada_en': datetime.utcnow().isoformat()
            }

        supabase.table('meta_publicaciones_webhook')                 .update(updates)                 .eq('post_id', post_id)                 .execute()

        # Actualizar datos_enriquecidos del webhook original (para frontend)
        try:
            webhook_result = supabase.table('logs_webhooks_meta')                     .select('id, datos_enriquecidos')                     .like('valor', f'%{post_id}%')                     .limit(1)                     .execute()

            if webhook_result.data:
                webhook = webhook_result.data[0]
                datos_enriq = webhook.get('datos_enriquecidos') or {}

                if tipo == 'video':
                    datos_enriq['video_local'] = url_public
                    datos_enriq['video_url_public'] = url_public
                    datos_enriq['video_storage_path'] = storage_path
                else:
                    datos_enriq['imagen_local'] = url_public
                    datos_enriq['thumbnail_url_public'] = url_public
                    datos_enriq['thumbnail_storage_path'] = storage_path

                supabase.table('logs_webhooks_meta')                         .update({'datos_enriquecidos': datos_enriq})                         .eq('id', webhook['id'])                         .execute()

                logger.info(f"✅ Webhook #{webhook['id']} actualizado para frontend")
        except Exception as webhook_err:
            logger.warning(f"⚠️ No se pudo actualizar webhook para frontend: {webhook_err}")

        logger.info(f"✅ Media descargado: {storage_path}")

        return {
            'success': True,
            'url_public': url_public,
            'storage_path': storage_path
        }

    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Error descargando: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Error guardando: {str(e)}'}

def extract_webhook_data(job):
    """
    Extrae post_id, item, verb, page_id del webhook según su tipo.
    
    Args:
        job (dict): Job de logs_webhooks_meta
        
    Returns:
        tuple: (post_id, item, verb, page_id) o (None, None, None, None) si no se puede extraer
    """
    try:
        valor = job.get('valor', {})
        if isinstance(valor, str):
            import json
            try:
                valor = json.loads(valor)
            except:
                return None, None, None, None
        
        # Determinar tipo de webhook
        tipo_objeto = job.get('tipo_objeto', 'feed')
        
        if tipo_objeto == 'feed':
            # Formato directo para feed
            # El page_id puede estar en el valor del webhook o en el campo page_id del job
            page_id = valor.get('recipient_id') or job.get('page_id')
            return valor.get('post_id'), valor.get('item', ''), valor.get('verb', ''), page_id
        
        elif tipo_objeto == 'webhook_raw_request':
            # Formato anidado para webhook_raw_request
            # Estructura: {entry: [{changes: [{value: {post_id, item, verb, ...}}], id: page_id}]}
            entry = valor.get('entry', [])
            if isinstance(entry, list) and entry:
                first_entry = entry[0]
                page_id = first_entry.get('id') or job.get('page_id')
                changes = first_entry.get('changes', [])
                if isinstance(changes, list) and changes:
                    change_value = changes[0].get('value', {})
                    return (
                        change_value.get('post_id'),
                        change_value.get('item', ''),
                        change_value.get('verb', ''),
                        page_id
                    )
        
        return None, None, None, None
    
    except Exception as e:
        logger.debug(f"Error extrayendo datos de webhook: {e}")
        return None, None, None, None


def get_pending_jobs():
    """
    Obtiene publicaciones pendientes de descargar media.
    
    Consulta directamente meta_publicaciones_webhook donde:
    - procesada = True (ya indexada)
    - video_local IS NULL o imagen_local IS NULL (falta descargar)
    - tipo_item in ['photo', 'video'] (no stories)
    
    Returns:
        list: Publicaciones a procesar
    """
    try:
        # Query directa a meta_publicaciones_webhook
        # Buscar publicaciones SIN media local descargada (más recientes primero)
        result = supabase.table('meta_publicaciones_webhook') \
            .select('id, post_id, nombre_nora, page_id, tipo_item, imagen_url, imagen_local, video_local, mensaje, created_time') \
            .eq('procesada', True) \
            .in_('tipo_item', ['photo', 'video']) \
            .order('created_time', desc=True) \
            .limit(BATCH_SIZE) \
            .execute()
        
        pubs = result.data or []
        
        # Filtrar por media faltante
        filtered = []
        for pub in pubs:
            tipo = pub.get('tipo_item')
            
            # Foto sin descargar
            if tipo == 'photo' and not pub.get('imagen_local') and pub.get('imagen_url'):
                filtered.append(pub)
            
            # Video sin descargar (y no es historia)
            elif tipo == 'video' and not pub.get('video_local'):
                # Verificar que NO sea historia (historias no tienen mensaje)
                mensaje = pub.get('mensaje', '')
                if mensaje and mensaje.strip():
                    filtered.append(pub)
        
        logger.info(f"📊 Jobs encontrados: {len(pubs)} total, {len(filtered)} listos para procesar")
        return filtered[:BATCH_SIZE]
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo jobs: {e}")
        return []


def process_job(job):
    """
    Procesa un job individual: descarga media y persiste en DB.
    
    Args:
        job (dict): Publicación de meta_publicaciones_webhook
        
    Returns:
        bool: True si éxito, False si error
    """
    pub_id = job['id']
    post_id = job['post_id']
    nombre_nora = job.get('nombre_nora', 'aura')
    tipo_item = job.get('tipo_item')
    page_id = job.get('page_id')
    
    try:
        logger.info(f"🔄 Procesando publicación #{pub_id}: {tipo_item} post={post_id} page={page_id}")
        
        # Ya tenemos la URL guardada - descargar directamente
        imagen_url = job.get('imagen_url')
        
        if not imagen_url:
            logger.warning(f"⚠️ Pub #{pub_id}: Sin imagen_url, omitiendo")
            return True
        
        # Descargar directamente desde la URL (sin consultar Facebook API)
        resultado = descargar_media_desde_url(
            url=imagen_url,
            post_id=post_id,
            nombre_nora=nombre_nora,
            tipo=tipo_item
        )
        
        if resultado['success']:
            logger.info(f"✅ Pub #{pub_id}: Media descargado")
            return True
        else:
            error_msg = resultado.get('error', 'Error desconocido')
            logger.warning(f"⚠️ Pub #{pub_id}: Error - {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Pub #{pub_id}: Excepción - {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def is_error_retriable(error_msg, error_detalle):
    """
    Determina si un error es reintetable.
    
    Errores NO reintetables:
    - 409 Conflict (archivo ya existe en storage - es éxito)
    - Token inválido permanente
    - Post eliminado / no existe
    - Permisos insuficientes claros
    
    Errores reintetables:
    - 429 Rate limit
    - Errores de red / timeouts
    - 500+ errores del servidor
    - Objeto temporalmente no disponible
    """
    error_lower = error_msg.lower()
    
    # 409 Conflict en storage NO es error (es idempotencia = éxito)
    # Esto no debería llegar aquí porque se trata como éxito en descargar_imagen_publicacion()
    if '409' in error_msg or 'conflict' in error_lower or 'already exists' in error_lower:
        logger.warning(f"⚠️ 409/conflict detectado en clasificación - debería ser éxito")
        return False  # NO reintentar (aunque es éxito, no error)
    
    # 429 Rate limit - RETRIABLE
    if '429' in error_msg or 'rate limit' in error_lower or 'too many' in error_lower:
        logger.info(f"🔄 Rate limit detectado - RETRIABLE")
        return True
    
    # Errores NO reintetables (permanentes)
    if 'no se pudo obtener datos del objeto' in error_lower:
        # Post eliminado o no existe
        return False
    
    if 'token' in error_lower and ('invalid' in error_lower or 'expired' in error_lower):
        return False
    
    if 'permission' in error_lower or 'permiso' in error_lower:
        return False
    
    # Analizar error_detalle de Facebook API si existe
    if isinstance(error_detalle, dict):
        error_obj = error_detalle.get('error', {})
        error_code = error_obj.get('code')
        error_type = error_obj.get('type')
        error_subcode = error_obj.get('error_subcode')
        
        # Rate limit (code 4 o 17)
        if error_code in [4, 17]:
            logger.info(f"🔄 Facebook API rate limit (code {error_code}) - RETRIABLE")
            return True
        
        # Errores temporales (code 1, 2)
        if error_code in [1, 2]:
            logger.info(f"🔄 Facebook API error temporal (code {error_code}) - RETRIABLE")
            return True
        
        # OAuthException puede ser retriable si es rate limit
        if error_type == 'OAuthException':
            if error_subcode == 2:  # Password changed / session expired
                return False
            if 'rate' in str(error_obj).lower() or 'limit' in str(error_obj).lower():
                return True
            # Otros OAuth => no retriable
            return False
        
        # Objeto no encontrado temporalmente (algunos 100)
        if error_code == 100:
            error_message = error_obj.get('message', '').lower()
            if 'unsupported' in error_message or 'does not exist' in error_message:
                return False  # Permanente
            else:
                return True  # Temporal
    
    # Timeouts / errores de red - RETRIABLES
    if 'timeout' in error_lower or 'timed out' in error_lower:
        return True
    
    if 'connection' in error_lower or 'network' in error_lower:
        return True
    
    # Errores 500+ del servidor - RETRIABLES
    if any(str(code) in error_msg for code in [500, 502, 503, 504]):
        return True
    
    # Por defecto: intentar retry (conservador)
    logger.info(f"🔄 Error no clasificado, asumiendo RETRIABLE: {error_msg[:100]}")
    return True


def mark_job_processing(job_id):
    """Marca job como PROCESSING para evitar doble procesamiento.
    
    Returns:
        bool: True si se marcó exitosamente, False si el job ya está en estado final
    """
    try:
        # Obtener datos actuales y verificar estado
        result = supabase.table('logs_webhooks_meta') \
            .select('datos_enriquecidos') \
            .eq('id', job_id) \
            .single() \
            .execute()
        
        enriq = result.data.get('datos_enriquecidos', {}) or {}
        current_estado = enriq.get('estado', 'PENDING')
        
        # NO pisar estados finales (otro worker ya completó)
        if current_estado in ['DONE', 'ERROR']:
            logger.warning(f"⚠️ Job #{job_id} ya está en estado final {current_estado}, abortando")
            return False
        
        # Marcar como PROCESSING
        enriq.update({
            'estado': 'PROCESSING',
            'processing_started_at': datetime.utcnow().isoformat()
        })
        
        # Mantener procesado=false mientras está en PROCESSING
        supabase.table('logs_webhooks_meta') \
            .update({'datos_enriquecidos': enriq}) \
            .eq('id', job_id) \
            .execute()
        
        logger.debug(f"🔄 Job #{job_id} marcado como PROCESSING")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Error marcando job #{job_id} como PROCESSING: {e}")
        return False


def mark_job_done(job_id, resultado=None, skip_download=False):
    """
    Marca job como DONE (procesado exitosamente).
    
    Args:
        job_id: ID del job
        resultado: Resultado de la descarga (si aplica)
        skip_download: Si es True, solo marca como DONE sin actualizar media (para historias)
    """
    try:
        enriq = {'estado': 'DONE', 'completed_at': datetime.utcnow().isoformat()}
        
        if skip_download:
            enriq['skipped'] = True
            enriq['skip_reason'] = 'Historia (video sin mensaje)'
        
        if resultado:
            enriq['resultado'] = resultado
        
        supabase.table('logs_webhooks_meta') \
            .update({
                'procesado': True,
                'procesado_en': datetime.utcnow().isoformat(),
                'datos_enriquecidos': enriq
            }) \
            .eq('id', job_id) \
            .execute()
        
        if skip_download:
            logger.info(f"✅ Job #{job_id} marcado como DONE (omitido - historia)")
        else:
            logger.info(f"✅ Job #{job_id} marcado como DONE")
        
        # CRÍTICO: Actualizar meta_publicaciones_webhook con imagen_local
        # Solo si NO es skip_download
        if not skip_download and resultado and resultado.get('success') and resultado.get('url_storage'):
            try:
                # Obtener post_id del job
                job_data = supabase.table('logs_webhooks_meta').select('valor').eq('id', job_id).single().execute()
                post_id = job_data.data.get('valor', {}).get('post_id')
                
                if post_id:
                    supabase.table('meta_publicaciones_webhook') \
                        .update({
                            'imagen_local': resultado.get('url_storage'),
                            'procesada': True,
                            'procesada_en': datetime.utcnow().isoformat()
                        }) \
                        .eq('post_id', post_id) \
                        .execute()
                    logger.info(f"✅ Actualizado meta_publicaciones_webhook para post {post_id}")
            except Exception as update_err:
                logger.error(f"❌ Error actualizando meta_publicaciones_webhook: {update_err}")
        
    except Exception as e:
        logger.error(f"❌ Error marcando job #{job_id} como DONE: {e}")


def mark_job_retry(job_id, error_msg, error_detalle=None):
    """Marca job para retry con backoff exponencial."""
    try:
        # Obtener datos actuales
        result = supabase.table('logs_webhooks_meta') \
            .select('datos_enriquecidos') \
            .eq('id', job_id) \
            .single() \
            .execute()
        
        enriq = result.data.get('datos_enriquecidos', {}) or {}
        attempts = enriq.get('attempts', 0) + 1
        
        if attempts > MAX_ATTEMPTS:
            logger.warning(f"⚠️ Job #{job_id} excedió máximo de intentos ({MAX_ATTEMPTS}), marcando ERROR")
            mark_job_error(job_id, f"Max retries exceeded: {error_msg}", error_detalle, non_retriable=True)
            return
        
        # Calcular next_retry_at con backoff
        delay_seconds = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)]
        next_retry_at = (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
        
        enriq.update({
            'estado': 'RETRY',
            'attempts': attempts,
            'next_retry_at': next_retry_at,
            'last_error': error_msg,
            'last_error_detalle': error_detalle,
            'last_attempt_at': datetime.utcnow().isoformat()
        })
        
        # CRÍTICO: Mantener procesado=false para que sea re-procesable
        supabase.table('logs_webhooks_meta') \
            .update({
                'datos_enriquecidos': enriq,
                'procesado': False  # Mantener FALSE en retries
            }) \
            .eq('id', job_id) \
            .execute()
        
        logger.info(f"🔄 Job #{job_id} marcado para retry (intento {attempts}/{MAX_ATTEMPTS}) en {delay_seconds}s")
        
    except Exception as e:
        logger.error(f"❌ Error marcando job #{job_id} para retry: {e}")


def mark_job_error(job_id, error_msg, error_detalle=None, non_retriable=False):
    """Marca job como ERROR final."""
    try:
        result = supabase.table('logs_webhooks_meta') \
            .select('datos_enriquecidos') \
            .eq('id', job_id) \
            .single() \
            .execute()
        
        enriq = result.data.get('datos_enriquecidos', {}) or {}
        
        enriq.update({
            'estado': 'ERROR',
            'error_final': error_msg,
            'error_detalle': error_detalle,
            'non_retriable': non_retriable,
            'failed_at': datetime.utcnow().isoformat()
        })
        
        supabase.table('logs_webhooks_meta') \
            .update({
                'procesado': True,
                'procesado_en': datetime.utcnow().isoformat(),
                'error_procesamiento': error_msg,
                'datos_enriquecidos': enriq
            }) \
            .eq('id', job_id) \
            .execute()
        
        logger.error(f"❌ Job #{job_id} marcado como ERROR: {error_msg}")
        
    except Exception as e:
        logger.error(f"❌ Error marcando job #{job_id} como ERROR: {e}")


def run_worker():
    """Loop principal del worker."""
    logger.info("🚀 Meta Media Worker iniciado")
    logger.info(f"⚙️ Configuración: batch_size={BATCH_SIZE}, poll_interval={POLL_INTERVAL}s, max_attempts={MAX_ATTEMPTS}")
    logger.info(f"⏱️ Retry delays: {RETRY_DELAYS}")
    
    # MODO TEST: Procesar últimos N eventos y salir
    if os.getenv('META_TEST_LAST_N'):
        try:
            n = int(os.getenv('META_TEST_LAST_N', '10'))
            tipo = os.getenv('META_TEST_TIPO', 'in_process_ad_objects')
            nombre_nora = os.getenv('META_TEST_NORA')
            
            logger.info(f"🧪 MODO TEST activado: procesando últimos {n} eventos tipo={tipo} nora={nombre_nora or 'ALL'}")
            procesados = procesar_ultimos_eventos(tipo_objeto=tipo, limit=n, nombre_nora=nombre_nora)
            logger.info(f"🧪 MODO TEST completado: {procesados} eventos procesados")
            return
        except Exception as e:
            logger.error(f"❌ Error en MODO TEST: {e}", exc_info=True)
            return

    last_ingest_run_ts = 0
    
    while True:
        try:
            now_ts = time.time()
            if now_ts - last_ingest_run_ts >= 300:
                try:
                    logger.info("🧩 Ingest webhooks Meta (logs_webhooks_meta) ejecutando...")
                    n_processed = procesar_eventos_pendientes()
                    logger.info(f"🧩 Ingest webhooks Meta terminado. Procesados: {n_processed}")
                except Exception as e:
                    logger.error(f"❌ Error procesando webhooks meta (ingest): {e}", exc_info=True)
                finally:
                    last_ingest_run_ts = now_ts

            jobs = get_pending_jobs()
            
            if not jobs:
                logger.debug(f"😴 No hay jobs pendientes, esperando {POLL_INTERVAL}s...")
                time.sleep(POLL_INTERVAL)
                continue
            
            logger.info(f"📦 Procesando batch de {len(jobs)} jobs")
            
            success_count = 0
            error_count = 0
            
            for job in jobs:
                if process_job(job):
                    success_count += 1
                else:
                    error_count += 1
                
                # Pequeña pausa entre jobs para no saturar API
                time.sleep(0.5)
            
            logger.info(f"✅ Batch completado: {success_count} éxito, {error_count} error/retry")
            
            # Pausa antes del siguiente batch
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 Worker detenido por usuario")
            break
        except Exception as e:
            logger.error(f"❌ Error en loop principal: {e}")
            import traceback
            logger.error(traceback.format_exc())
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear app context
    app = create_app()
    if isinstance(app, tuple):
        app = app[0]
    
    with app.app_context():
        run_worker()
