"""
Servicio para descargar media de publicaciones Meta desde webhooks.
Descarga imágenes y videos desde URLs de Facebook y los almacena en Supabase Storage.
"""
import logging
import requests
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Configuración
BATCH_SIZE = 50
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 5  # Máximo de reintentos por webhook


def _registrar_error(supabase, post_id: str, error_msg: str, error_type: str):
    """
    Registra un error en media_last_error y actualiza media_status.
    Incrementa media_attempts.
    """
    try:
        # Obtener intentos actuales
        result = supabase.table('meta_publicaciones_webhook') \
            .select('media_attempts') \
            .eq('post_id', post_id) \
            .single() \
            .execute()
        
        attempts = (result.data.get('media_attempts') or 0) + 1
        
        # Determinar estado
        status = 'error' if attempts >= MAX_ATTEMPTS else 'pending'
        
        # Actualizar
        supabase.table('meta_publicaciones_webhook') \
            .update({
                'media_status': status,
                'media_attempts': attempts,
                'media_last_error': {
                    'message': error_msg,
                    'type': error_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'attempt': attempts
                },
                'media_updated_at': datetime.utcnow().isoformat()
            }) \
            .eq('post_id', post_id) \
            .execute()
        
        if attempts >= MAX_ATTEMPTS:
            logger.error(f"❌ Post {post_id} alcanzó máximo de intentos ({MAX_ATTEMPTS})")
        else:
            logger.info(f"🔄 Post {post_id} reintentará (intento {attempts}/{MAX_ATTEMPTS})")
    
    except Exception as e:
        logger.error(f"Error registrando error para {post_id}: {e}")


def descargar_media_desde_url(
    supabase,
    url: str,
    post_id: str,
    nombre_nora: str,
    tipo: str,
    bucket_name: str = 'meta-webhooks'
) -> Dict[str, any]:
    """
    Descarga media directamente desde URL de Facebook y guarda en Supabase Storage.

    Args:
        supabase: Cliente de Supabase
        url: URL de la imagen/video en Facebook
        post_id: ID del post (para nombrar archivo)
        nombre_nora: Tenant/cliente
        tipo: 'photo' o 'video'
        bucket_name: Nombre del bucket en Supabase Storage

    Returns:
        dict: {'success': bool, 'url_public': str, 'storage_path': str, 'error': str}
    """
    try:
        logger.info(f"📥 Descargando {tipo} desde: {url[:80]}...")
        
        # Descargar archivo desde Facebook
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()

        # Determinar extensión del archivo
        content_type = response.headers.get('content-type', '')
        ext = mimetypes.guess_extension(content_type)
        
        # Fallback para tipos comunes
        if not ext:
            if tipo == 'video':
                ext = '.mp4'
            elif 'image' in content_type:
                ext = '.jpg'
            else:
                ext = '.bin'

        # Nombre de archivo único
        filename = f"{post_id.replace('/', '_')}{ext}"

        # Path en Supabase Storage
        storage_path = f"{nombre_nora}/publicaciones_meta/{filename}"

        logger.debug(f"  Subiendo a Storage: {storage_path}")
        
        # Marcar como descargando
        supabase.table('meta_publicaciones_webhook') \
            .update({
                'media_status': 'downloading',
                'media_updated_at': datetime.utcnow().isoformat()
            }) \
            .eq('post_id', post_id) \
            .execute()
        
        # Subir a Supabase Storage (con upsert para idempotencia)
        try:
            supabase.storage.from_(bucket_name).upload(
                path=storage_path,
                file=response.content,
                file_options={"content-type": content_type or "application/octet-stream", "upsert": "true"}
            )
            logger.info(f"✅ Archivo subido exitosamente: {storage_path}")
        except Exception as upload_err:
            # Si el archivo ya existe (409 Conflict), no es error
            error_str = str(upload_err).lower()
            if '409' in error_str or 'already exists' in error_str or 'duplicate' in error_str:
                logger.info(f"⚠️ Archivo ya existe en storage (idempotencia): {storage_path}")
            else:
                raise

        # Obtener URL pública
        url_public = supabase.storage.from_(bucket_name).get_public_url(storage_path)

        # Actualizar meta_publicaciones_webhook con URLs y paths
        if tipo == 'video':
            updates = {
                'video_local': url_public,
                'video_url_public': url_public,
                'video_storage_path': storage_path,
                'video_descargado_en': datetime.utcnow().isoformat(),
                'procesada': True,
                'procesada_en': datetime.utcnow().isoformat(),
                'media_status': 'success',
                'media_updated_at': datetime.utcnow().isoformat(),
                'media_last_error': None
            }
        else:  # photo
            updates = {
                'imagen_local': url_public,
                'imagen_descargada_en': datetime.utcnow().isoformat(),
                'procesada': True,
                'procesada_en': datetime.utcnow().isoformat(),
                'media_status': 'success',
                'media_updated_at': datetime.utcnow().isoformat(),
                'media_last_error': None
            }

        supabase.table('meta_publicaciones_webhook') \
            .update(updates) \
            .eq('post_id', post_id) \
            .execute()

        logger.info(f"✅ Base de datos actualizada para post {post_id}")

        return {
            'success': True,
            'url_public': url_public,
            'storage_path': storage_path
        }

    except requests.exceptions.Timeout:
        error_msg = f"Timeout descargando {tipo} (>{TIMEOUT_SECONDS}s)"
        logger.warning(f"⚠️ {error_msg}")
        _registrar_error(supabase, post_id, error_msg, 'timeout')
        return {'success': False, 'error': error_msg}
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Error HTTP descargando {tipo}: {str(e)}"
        logger.warning(f"⚠️ {error_msg}")
        _registrar_error(supabase, post_id, error_msg, 'http_error')
        return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Error guardando en Storage: {str(e)}"
        logger.error(f"❌ {error_msg}")
        import traceback
        logger.debug(traceback.format_exc())
        _registrar_error(supabase, post_id, error_msg, 'storage_error')
        return {'success': False, 'error': error_msg}


def extract_webhook_data(webhook: Dict) -> tuple:
    """
    Extrae datos del webhook de logs_webhooks_meta.
    
    Returns:
        tuple: (post_id, item, verb, page_id, imagen_url) o (None, None, None, None, None)
    """
    try:
        import json
        
        valor = webhook.get('valor', {})
        if isinstance(valor, str):
            try:
                valor = json.loads(valor)
            except:
                return None, None, None, None, None
        
        tipo_objeto = webhook.get('tipo_objeto', 'feed')
        
        if tipo_objeto == 'feed':
            page_id = valor.get('recipient_id') or webhook.get('page_id')
            return (
                valor.get('post_id'),
                valor.get('item', ''),
                valor.get('verb', ''),
                page_id,
                valor.get('photo') or valor.get('link')
            )
        
        elif tipo_objeto == 'webhook_raw_request':
            entry = valor.get('entry', [])
            if isinstance(entry, list) and entry:
                first_entry = entry[0]
                page_id = first_entry.get('id') or webhook.get('page_id')
                changes = first_entry.get('changes', [])
                if isinstance(changes, list) and changes:
                    change_value = changes[0].get('value', {})
                    return (
                        change_value.get('post_id'),
                        change_value.get('item', ''),
                        change_value.get('verb', ''),
                        page_id,
                        change_value.get('photo') or change_value.get('link')
                    )
        
        return None, None, None, None, None
    
    except Exception as e:
        logger.debug(f"Error extrayendo datos de webhook: {e}")
        return None, None, None, None, None


def get_webhooks_pendientes(supabase, limit: int = BATCH_SIZE) -> List[Dict]:
    """
    Obtiene webhooks pendientes de procesar desde logs_webhooks_meta.
    
    Criterios:
    - estado IN ('PENDING', 'RETRY')
    - tipo_objeto = 'feed' (publicaciones de Facebook)
    - attempt < MAX_ATTEMPTS
    
    Returns:
        Lista de webhooks a procesar (más recientes primero)
    """
    try:
        logger.debug(f"🔍 Buscando webhooks pendientes (límite: {limit})...")
        
        # Query a logs_webhooks_meta
        result = supabase.table('logs_webhooks_meta') \
            .select('id, tipo_objeto, objeto_id, campo, valor, nombre_nora, page_id, datos_enriquecidos, attempt, timestamp') \
            .in_('estado', ['PENDING', 'RETRY']) \
            .eq('tipo_objeto', 'feed') \
            .lt('attempt', MAX_ATTEMPTS) \
            .order('timestamp', desc=True) \
            .limit(limit) \
            .execute()
        
        webhooks = result.data or []
        
        logger.info(f"📊 Encontrados {len(webhooks)} webhooks pendientes")
        
        return webhooks
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo webhooks pendientes: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []


def procesar_webhook(supabase, webhook: Dict) -> bool:
    """
    Procesa un webhook individual: descarga media y actualiza BD.
    
    Args:
        supabase: Cliente de Supabase
        webhook: Dict con datos del webhook de logs_webhooks_meta
        
    Returns:
        bool: True si éxito, False si error
    """
    webhook_id = webhook['id']
    nombre_nora = webhook.get('nombre_nora', 'default')
    attempt = webhook.get('attempt') or 0
    
    try:
        # Extraer datos del webhook
        post_id, item, verb, page_id, imagen_url = extract_webhook_data(webhook)
        
        if not post_id:
            logger.warning(f"⚠️ Webhook #{webhook_id}: No se pudo extraer post_id, marcando como procesado")
            marcar_webhook_procesado(supabase, webhook_id)
            return True
        
        logger.info(f"🔄 Procesando webhook #{webhook_id}: post={post_id} (intento {attempt + 1}/{MAX_ATTEMPTS})")
        
        # Verificar si ya existe en meta_publicaciones_webhook
        pub_existente = supabase.table('meta_publicaciones_webhook') \
            .select('imagen_local, video_local') \
            .eq('post_id', post_id) \
            .single() \
            .execute()
        
        # Si ya tiene media descargado, marcar webhook como procesado
        if pub_existente.data:
            if item == 'photo' and pub_existente.data.get('imagen_local'):
                logger.info(f"✅ Webhook #{webhook_id}: Foto ya descargada previamente")
                marcar_webhook_procesado(supabase, webhook_id)
                return True
            elif item == 'video' and pub_existente.data.get('video_local'):
                logger.info(f"✅ Webhook #{webhook_id}: Video ya descargado previamente")
                marcar_webhook_procesado(supabase, webhook_id)
                return True
        
        if not imagen_url:
            logger.warning(f"⚠️ Webhook #{webhook_id}: Sin imagen_url, marcando como procesado")
            marcar_webhook_procesado(supabase, webhook_id)
            return True
        
        # Descargar media
        resultado = descargar_media_desde_url(
            supabase=supabase,
            url=imagen_uwebhooks pendientes.
    
    Returns:
        Dict con estadísticas: {'procesados': int, 'exitosos': int, 'errores': int}
    """
    stats = {
        'procesados': 0,
        'exitosos': 0,
        'errores': 0
    }
    
    try:
        # Obtener webhooks pendientes
        webhooks = get_webhooks_pendientes(supabase, limit=batch_size)
        
        if not webhooks:
            logger.info("😴 No hay webhooks pendientes de procesar")
            return stats
        
        logger.info(f"📦 Procesando batch de {len(webhooks)} webhooks")
        
        # Procesar cada webhook
        for webhook in webhooks:
            stats['procesados'] += 1
            
            if procesar_webhook(supabase, webhook):
                stats['exitosos'] += 1
            else:
                stats['errores'] += 1
        
        logger.info(
            f"✅ Batch completado: {stats['exitosos']} exitosos, "
            f"{stats['errores']} errores de {stats['procesados']} procesado
            .eq('id', webhook_id) \
            .execute()
    except Exception as e:
        logger.error(f"Error marcando webhook #{webhook_id} como procesado: {e}")


def marcar_webhook_error(supabase, webhook_id: int, error_msg: str, attempt: int):
    """Marca un webhook con error para retry."""
    try:
        new_attempt = attempt + 1
        estado = 'ERROR' if new_attempt >= MAX_ATTEMPTS else 'RETRY'
        
        supabase.table('logs_webhooks_meta') \
            .update({
                'estado': estado,
                'attempt': new_attempt,
                'error_message': error_msg,
                'next_retry': (datetime.utcnow() + timedelta(minutes=5)).isoformat() if estado == 'RETRY' else None
            }) \
            .eq('id', webhook_id) \
            .execute()
        
        if estado == 'ERROR':
            logger.error(f"❌ Webhook #{webhook_id} alcanzó máximo de intentos ({MAX_ATTEMPTS})")
    except Exception as e:
        logger.error(f"Error marcando webhook #{webhook_id} con error: {e}")


def procesar_batch(supabase, batch_size: int = BATCH_SIZE) -> Dict[str, int]:
    """
    Procesa un batch de publicaciones pendientes.
    
    Returns:
        Dict con estadísticas: {'procesadas': int, 'exitosas': int, 'errores': int}
    """
    stats = {
        'procesadas': 0,
        'exitosas': 0,
        'errores': 0
    }
    
    try:
        # Obtener publicaciones pendientes
        pendientes = get_publicaciones_pendientes(supabase, limit=batch_size)
        
        if not pendientes:
            logger.info("😴 No hay publicaciones pendientes de descargar")
            return stats
        
        logger.info(f"📦 Procesando batch de {len(pendientes)} publicaciones")
        
        # Procesar cada publicación
        for pub in pendientes:
            stats['procesadas'] += 1
            
            if procesar_publicacion(supabase, pub):
                stats['exitosas'] += 1
            else:
                stats['errores'] += 1
        
        logger.info(
            f"✅ Batch completado: {stats['exitosas']} exitosas, "
            f"{stats['errores']} errores de {stats['procesadas']} procesadas"
        )
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Error procesando batch: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return stats
