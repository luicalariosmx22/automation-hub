"""
Job para subir videos a YouTube Shorts automáticamente desde Facebook
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from automation_hub.config.logging import setup_logging
from automation_hub.db.supabase_client import get_supabase_client
from automation_hub.integrations.youtube.youtube_service import YouTubeService
from automation_hub.integrations.telegram.notifier import TelegramNotifier

setup_logging()
logger = logging.getLogger(__name__)

# Configuración
MAX_VIDEOS_PER_RUN = 5  # Límite de videos por ejecución
VIDEO_DELAY_SECONDS = 120  # 2 minutos entre videos

def es_url_valida_para_youtube(url: str) -> bool:
    """
    Valida que la URL sea de Supabase Storage
    
    Args:
        url: URL del video
        
    Returns:
        True si es válida
    """
    if not url:
        return False
    
    return 'supabase' in url.lower() and 'storage' in url.lower()

def descargar_video_temporal(video_url: str, publicacion_id: str) -> str:
    """
    Descarga video de Supabase a archivo temporal
    
    Args:
        video_url: URL del video en Supabase
        publicacion_id: ID de la publicación (para nombre único)
        
    Returns:
        Ruta al archivo temporal
    """
    import requests
    import tempfile
    
    # Crear directorio temporal
    temp_dir = Path(tempfile.gettempdir()) / 'youtube_uploads'
    temp_dir.mkdir(exist_ok=True)
    
    # Nombre del archivo
    filename = f"video_{publicacion_id}.mp4"
    filepath = temp_dir / filename
    
    # Descargar
    logger.info(f"Descargando video desde: {video_url}")
    response = requests.get(video_url, stream=True, timeout=60)
    response.raise_for_status()
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    logger.info(f"Video descargado: {filepath}")
    return str(filepath)

def limpiar_archivo_temporal(filepath: str):
    """Elimina archivo temporal después de subir"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Archivo temporal eliminado: {filepath}")
    except Exception as e:
        logger.warning(f"Error eliminando archivo temporal: {e}")

def obtener_nombre_cliente(supabase, cliente_id: str) -> str:
    """Obtiene nombre del cliente para notificaciones"""
    try:
        result = supabase.table('cliente_empresas').select(
            'title, store_code'
        ).eq('id', cliente_id).execute()
        
        if result.data and len(result.data) > 0:
            empresa = result.data[0]
            return empresa.get('title') or empresa.get('store_code', 'Cliente')
        
        return 'Cliente'
    except Exception as e:
        logger.warning(f"Error obteniendo nombre cliente: {e}")
        return 'Cliente'

def subir_videos_a_youtube():
    """
    Job principal: Busca videos de Facebook y los sube a YouTube Shorts
    """
    logger.info("=" * 80)
    logger.info("Iniciando job de YouTube Shorts")
    logger.info("=" * 80)
    
    supabase = get_supabase_client()
    youtube_service = YouTubeService(
        supabase,
        os.getenv('YOUTUBE_CLIENT_SECRETS_FILE', 'youtube_client_secrets.json')
    )
    telegram = TelegramNotifier()
    
    try:
        # Buscar publicaciones de video pendientes de subir a YouTube
        # Criterios:
        # 1. Tienen video_url válido
        # 2. publicada_gbp = true (ya se publicó en GBP)
        # 3. No están ya en youtube_videos
        # 4. Cliente tiene YouTube conectado
        # 5. Fecha reciente (últimos 7 días)
        
        fecha_limite = (datetime.now() - timedelta(days=7)).isoformat()
        
        result = supabase.table('meta_publicaciones_webhook').select(
            'id, cliente_id, post_id, message, video_url, image_url, created_time'
        ).eq('publicada_gbp', True).gte(
            'created_time',
            fecha_limite
        ).order('created_time', desc=True).limit(50).execute()
        
        publicaciones = result.data
        logger.info(f"Encontradas {len(publicaciones)} publicaciones de GBP")
        
        # Filtrar las que tienen video y no están en YouTube
        videos_subidos = 0
        
        for pub in publicaciones:
            if videos_subidos >= MAX_VIDEOS_PER_RUN:
                logger.info(f"Límite alcanzado: {MAX_VIDEOS_PER_RUN} videos por ejecución")
                break
            
            # Verificar si tiene video válido
            video_url = pub.get('video_url')
            if not video_url or not es_url_valida_para_youtube(video_url):
                continue
            
            # Verificar si cliente tiene YouTube conectado
            cliente_id = pub['cliente_id']
            if not youtube_service.is_connected(cliente_id):
                logger.debug(f"Cliente {cliente_id} no tiene YouTube conectado")
                continue
            
            # Verificar si ya fue subido a YouTube
            check = supabase.table('youtube_videos').select('id').eq(
                'source_type',
                'facebook_post'
            ).eq('source_id', pub['post_id']).execute()
            
            if check.data and len(check.data) > 0:
                logger.debug(f"Post {pub['post_id']} ya está en YouTube")
                continue
            
            # Subir a YouTube
            try:
                logger.info(f"Procesando video: {pub['post_id']}")
                
                # Descargar video temporal
                video_path = descargar_video_temporal(video_url, pub['id'])
                
                # Preparar metadata
                title = pub.get('message', '')[:100] or f"Video {pub['post_id']}"
                description = pub.get('message', '')[:5000]
                
                # Obtener nombre del cliente
                nombre_cliente = obtener_nombre_cliente(supabase, cliente_id)
                
                # Subir a YouTube
                resultado = youtube_service.upload_video(
                    cliente_id=cliente_id,
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=['shorts', 'facebook', 'automation'],
                    privacy_status='public',
                    validate_shorts=True,
                    source_type='facebook_post',
                    source_id=pub['post_id']
                )
                
                videos_subidos += 1
                
                # Limpiar archivo temporal
                limpiar_archivo_temporal(video_path)
                
                # Enviar notificación Telegram
                mensaje = (
                    f"📹 *Video subido a YouTube Shorts*\n\n"
                    f"*Negocio:* {nombre_cliente}\n"
                    f"*Título:* {title}\n"
                    f"*URL:* {resultado['url']}\n"
                    f"*Short:* {'Sí' if resultado.get('is_short') else 'No'}\n"
                    f"*Estado:* Público"
                )
                
                telegram.enviar_notificacion(
                    mensaje=mensaje,
                    nivel='info',
                    categoria='youtube_upload'
                )
                
                logger.info(f"✅ Video subido: {resultado['url']}")
                
                # Delay entre videos
                if videos_subidos < MAX_VIDEOS_PER_RUN:
                    import time
                    logger.info(f"Esperando {VIDEO_DELAY_SECONDS}s antes del siguiente video...")
                    time.sleep(VIDEO_DELAY_SECONDS)
                
            except Exception as e:
                logger.error(f"Error subiendo video {pub['post_id']}: {e}", exc_info=True)
                
                # Notificar error
                telegram.enviar_notificacion(
                    mensaje=(
                        f"❌ *Error subiendo video a YouTube*\n\n"
                        f"*Post:* {pub['post_id']}\n"
                        f"*Error:* {str(e)}"
                    ),
                    nivel='error',
                    categoria='youtube_upload'
                )
                
                continue
        
        logger.info(f"Job finalizado. Videos subidos: {videos_subidos}")
        
    except Exception as e:
        logger.error(f"Error en job de YouTube: {e}", exc_info=True)
        
        telegram.enviar_notificacion(
            mensaje=f"❌ *Error en job de YouTube Shorts*\n\n{str(e)}",
            nivel='error',
            categoria='youtube_upload'
        )

if __name__ == '__main__':
    subir_videos_a_youtube()
