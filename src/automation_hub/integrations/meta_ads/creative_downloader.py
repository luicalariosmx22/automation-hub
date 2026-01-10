"""
Servicio para descargar creativos de anuncios Meta desde webhooks.
Descarga imágenes de ad creatives y los almacena en Supabase Storage.
"""
import logging
import requests
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Configuración
BATCH_SIZE = 100
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 5  # Máximo de reintentos por webhook


def extract_ad_webhook_data(webhook: Dict) -> tuple:
    """
    Extrae datos de anuncios del webhook de logs_webhooks_meta.
    
    Returns:
        tuple: (creative_id, creative_image_url, cuenta_publicitaria) o (None, None, None)
    """
    try:
        import json
        
        datos_enriquecidos = webhook.get('datos_enriquecidos', {})
        if isinstance(datos_enriquecidos, str):
            try:
                datos_enriquecidos = json.loads(datos_enriquecidos)
            except:
                datos_enriquecidos = {}
        
        # Extraer datos del anuncio
        creative_id = datos_enriquecidos.get('creative_id')
        creative_image = datos_enriquecidos.get('creative_image')
        cuenta_publicitaria = webhook.get('id_cuenta_publicitaria')
        
        if creative_id and creative_image:
            return creative_id, creative_image, cuenta_publicitaria
        
        return None, None, None
    
    except Exception as e:
        logger.debug(f"Error extrayendo datos de webhook de anuncio: {e}")
        return None, None, None


def get_webhooks_anuncios_pendientes(supabase, limit: int = BATCH_SIZE) -> List[Dict]:
    """
    Obtiene webhooks de anuncios pendientes de procesar desde logs_webhooks_meta.
    
    Criterios:
    - estado IN ('PENDING', 'RETRY')
    - tipo_objeto IN ('ad', 'adcreative') 
    - datos_enriquecidos->'creative_image' IS NOT NULL
    - attempt < MAX_ATTEMPTS
    
    Returns:
        Lista de webhooks a procesar (más recientes primero)
    """
    try:
        logger.debug(f"🔍 Buscando webhooks de anuncios pendientes (límite: {limit})...")
        
        # Query a logs_webhooks_meta
        result = supabase.table('logs_webhooks_meta') \
            .select('id, tipo_objeto, objeto_id, nombre_nora, id_cuenta_publicitaria, datos_enriquecidos, attempt, timestamp') \
            .in_('estado', ['PENDING', 'RETRY']) \
            .in_('tipo_objeto', ['ad', 'adcreative']) \
            .lt('attempt', MAX_ATTEMPTS) \
            .order('timestamp', desc=True) \
            .limit(limit) \
            .execute()
        
        webhooks = result.data or []
        
        # Filtrar solo los que tienen creative_image
        webhooks_con_imagen = []
        for wh in webhooks:
            creative_id, creative_image, _ = extract_ad_webhook_data(wh)
            if creative_id and creative_image:
                webhooks_con_imagen.append(wh)
        
        logger.info(f"📊 Encontrados {len(webhooks)} webhooks de anuncios, {len(webhooks_con_imagen)} con imagen")
        
        return webhooks_con_imagen
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo webhooks de anuncios: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []


def descargar_creativo_desde_url(
    supabase,
    url: str,
    creative_id: str,
    nombre_nora: str,
    bucket_name: str = 'meta-webhooks'
) -> Dict:
    """
    Descarga creativo de anuncio desde URL de Facebook y guarda en Supabase Storage.

    Args:
        supabase: Cliente de Supabase
        url: URL de la imagen del creativo en Facebook
        creative_id: ID del creativo (para nombrar archivo)
        nombre_nora: Tenant/cliente
        bucket_name: Nombre del bucket en Supabase Storage

    Returns:
        dict: {'success': bool, 'url_public': str, 'storage_path': str, 'error': str}
    """
    try:
        logger.info(f"📥 Descargando creativo desde: {url[:80]}...")
        
        # Descargar archivo desde Facebook
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()

        # Determinar extensión del archivo
        content_type = response.headers.get('content-type', '')
        ext = mimetypes.guess_extension(content_type)
        
        # Fallback para tipos comunes
        if not ext:
            if 'image' in content_type:
                ext = '.jpg'
            else:
                ext = '.jpg'  # Default para creativos

        # Nombre de archivo único
        filename = f"{creative_id.replace('/', '_')}{ext}"

        # Path en Supabase Storage (carpeta diferente para anuncios)
        storage_path = f"{nombre_nora}/anuncios_meta/{filename}"

        logger.debug(f"  Subiendo a Storage: {storage_path}")
        
        # Subir a Supabase Storage (con upsert para idempotencia)
        try:
            supabase.storage.from_(bucket_name).upload(
                path=storage_path,
                file=response.content,
                file_options={"content-type": content_type or "image/jpeg", "upsert": "true"}
            )
            logger.info(f"✅ Creativo subido exitosamente: {storage_path}")
        except Exception as upload_err:
            # Si el archivo ya existe (409 Conflict), no es error
            error_str = str(upload_err).lower()
            if '409' in error_str or 'already exists' in error_str or 'duplicate' in error_str:
                logger.info(f"⚠️ Creativo ya existe en storage (idempotencia): {storage_path}")
            else:
                raise

        # Obtener URL pública
        url_public = supabase.storage.from_(bucket_name).get_public_url(storage_path)

        # Actualizar meta_ads_anuncios_webhooks con URL local
        updates = {
            'creative_image_local': url_public,
            'last_synced': datetime.utcnow().isoformat()
        }

        supabase.table('meta_ads_anuncios_webhooks') \
            .update(updates) \
            .eq('creative_id', creative_id) \
            .execute()

        logger.info(f"✅ Base de datos actualizada para creativo {creative_id}")

        return {
            'success': True,
            'url_public': url_public,
            'storage_path': storage_path
        }

    except requests.exceptions.Timeout:
        error_msg = f"Timeout descargando creativo (>{TIMEOUT_SECONDS}s)"
        logger.warning(f"⚠️ {error_msg}")
        return {'success': False, 'error': error_msg}
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Error HTTP descargando creativo: {str(e)}"
        logger.warning(f"⚠️ {error_msg}")
        return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Error guardando en Storage: {str(e)}"
        logger.error(f"❌ {error_msg}")
        import traceback
        logger.debug(traceback.format_exc())
        return {'success': False, 'error': error_msg}


def procesar_webhook_anuncio(supabase, webhook: Dict) -> bool:
    """
    Procesa un webhook de anuncio: descarga creative y actualiza BD.
    
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
        creative_id, creative_image_url, cuenta_publicitaria = extract_ad_webhook_data(webhook)
        
        if not creative_id:
            logger.warning(f"⚠️ Webhook #{webhook_id}: No se pudo extraer creative_id, marcando como procesado")
            marcar_webhook_procesado(supabase, webhook_id)
            return True
        
        logger.info(f"🔄 Procesando webhook #{webhook_id}: creative={creative_id} (intento {attempt + 1}/{MAX_ATTEMPTS})")
        
        # Verificar si ya existe en meta_ads_anuncios_webhooks con creative descargado
        try:
            ad_existente = supabase.table('meta_ads_anuncios_webhooks') \
                .select('creative_image_local') \
                .eq('creative_id', creative_id) \
                .limit(1) \
                .execute()
            
            # Si ya tiene creative descargado, marcar webhook como procesado
            if ad_existente.data and ad_existente.data[0].get('creative_image_local'):
                logger.info(f"✅ Webhook #{webhook_id}: Creative ya descargado previamente")
                marcar_webhook_procesado(supabase, webhook_id)
                return True
        except:
            pass  # Si no existe, continuar con descarga
        
        if not creative_image_url:
            logger.warning(f"⚠️ Webhook #{webhook_id}: Sin creative_image_url, marcando como procesado")
            marcar_webhook_procesado(supabase, webhook_id)
            return True
        
        # Descargar creative
        resultado = descargar_creativo_desde_url(
            supabase=supabase,
            url=creative_image_url,
            creative_id=creative_id,
            nombre_nora=nombre_nora
        )
        
        if resultado['success']:
            logger.info(f"✅ Webhook #{webhook_id}: Creative descargado exitosamente")
            marcar_webhook_procesado(supabase, webhook_id)
            return True
        else:
            error_msg = resultado.get('error', 'Error desconocido')
            logger.warning(f"⚠️ Webhook #{webhook_id}: Error - {error_msg}")
            marcar_webhook_error(supabase, webhook_id, error_msg, attempt)
            return False
            
    except Exception as e:
        logger.error(f"❌ Webhook #{webhook_id}: Excepción - {e}")
        import traceback
        logger.error(traceback.format_exc())
        marcar_webhook_error(supabase, webhook_id, str(e), attempt)
        return False


def marcar_webhook_procesado(supabase, webhook_id: int):
    """Marca un webhook como procesado exitosamente."""
    try:
        supabase.table('logs_webhooks_meta') \
            .update({
                'procesado': True,
                'procesado_en': datetime.utcnow().isoformat(),
                'estado': 'DONE'
            }) \
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
                'next_retry': (datetime.utcnow() + timedelta(minutes=10)).isoformat() if estado == 'RETRY' else None
            }) \
            .eq('id', webhook_id) \
            .execute()
        
        if estado == 'ERROR':
            logger.error(f"❌ Webhook #{webhook_id} alcanzó máximo de intentos ({MAX_ATTEMPTS})")
    except Exception as e:
        logger.error(f"Error marcando webhook #{webhook_id} con error: {e}")


def procesar_batch(supabase, batch_size: int = BATCH_SIZE) -> Dict[str, int]:
    """
    Procesa un batch de webhooks de anuncios pendientes.
    
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
        webhooks = get_webhooks_anuncios_pendientes(supabase, limit=batch_size)
        
        if not webhooks:
            logger.info("😴 No hay webhooks de anuncios pendientes de procesar")
            return stats
        
        logger.info(f"📦 Procesando batch de {len(webhooks)} webhooks de anuncios")
        
        # Procesar cada webhook
        for webhook in webhooks:
            stats['procesados'] += 1
            
            if procesar_webhook_anuncio(supabase, webhook):
                stats['exitosos'] += 1
            else:
                stats['errores'] += 1
        
        logger.info(
            f"✅ Batch completado: {stats['exitosos']} exitosos, "
            f"{stats['errores']} errores de {stats['procesados']} procesados"
        )
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Error procesando batch: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return stats
