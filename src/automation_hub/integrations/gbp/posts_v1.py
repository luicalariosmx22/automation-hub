"""
Cliente para Google Business Profile Local Posts API v1.
"""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Variable global para cache del account ID
_cached_account_id = None

def gbp_media_create_video(
    account_id: str,
    location_id: str, 
    video_url: str,
    auth_header: dict
) -> dict:
    """
    Sube un video a la galería de Google Business Profile usando Media.Create.
    
    Args:
        account_id: ID de la cuenta (formato: accounts/XXXXX)
        location_id: ID de la ubicación (formato: locations/YYYY) 
        video_url: URL del video a subir
        auth_header: Header de autorización
        
    Returns:
        Respuesta de la API con datos del media creado
        
    Raises:
        requests.exceptions.HTTPError: Si la API retorna error
    """
    # Construir el nombre completo de la ubicación si es necesario
    if not location_id.startswith("accounts/"):
        if location_id.startswith("locations/"):
            full_location = f"{account_id}/{location_id}"
        else:
            full_location = f"{account_id}/locations/{location_id}"
    else:
        full_location = location_id
    
    base_url = "https://mybusiness.googleapis.com/v4"
    url = f"{base_url}/{full_location}/media"
    
    payload = {
        "mediaFormat": "VIDEO",
        "locationAssociation": {
            "category": "ADDITIONAL"
        },
        "sourceUrl": video_url
    }
    
    try:
        logger.info(f"📹 Subiendo video a GBP Media Gallery: {video_url[:50]}...")
        response = requests.post(url, headers=auth_header, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"✅ VIDEO -> GBP Media Gallery exitoso: {data.get('name', 'N/A')}")
        
        # Log de datos relevantes para auditoría
        if isinstance(data, dict):
            logger.info(f"📊 Video media details:")
            logger.info(f"   🆔 Name: {data.get('name', 'N/A')}")
            logger.info(f"   🔗 GoogleUrl: {data.get('googleUrl', 'N/A')}")
            logger.info(f"   🖼️ ThumbnailUrl: {data.get('thumbnailUrl', 'N/A')}")
            logger.info(f"   📅 CreateTime: {data.get('createTime', 'N/A')}")
        
        return data
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP error subiendo video a GBP Media: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error subiendo video a GBP Media: {e}")
        raise

def detect_video_content(video_local: Optional[str] = None, imagen_local: Optional[str] = None, imagen_url: Optional[str] = None) -> tuple[bool, str]:
    """
    Detecta si el contenido es video y retorna la URL a usar.
    
    Args:
        video_local: URL del video en Supabase (prioridad máxima)
        imagen_local: URL de imagen en Supabase
        imagen_url: URL original de imagen/video
        
    Returns:
        Tuple (es_video: bool, url: str)
    """
    # 1. Priorizar video_local si existe
    if video_local:
        logger.info(f"🎯 Video detectado en video_local: {video_local[:50]}...")
        return True, video_local
    
    # 2. Verificar imagen_local si contiene video
    if imagen_local:
        video_extensions = ['.mp4', '.mov', '.m4v', '.avi', '.webm', '.3gp', '.flv']
        if any(ext in imagen_local.lower() for ext in video_extensions):
            logger.info(f"🎬 Video detectado en imagen_local: {imagen_local[:50]}...")
            return True, imagen_local
    
    # 3. Verificar imagen_url si contiene video
    if imagen_url:
        video_extensions = ['.mp4', '.mov', '.m4v', '.avi', '.webm', '.3gp', '.flv']
        video_patterns = ['video.', '/v/', '/o1/v/', 'bitrate=']
        
        if (any(ext in imagen_url.lower() for ext in video_extensions) or 
            any(pattern in imagen_url.lower() for pattern in video_patterns)):
            logger.info(f"📹 Video detectado en imagen_url: {imagen_url[:50]}...")
            return True, imagen_url
    
    # No es video, devolver la primera imagen disponible
    for url in [imagen_local, imagen_url]:
        if url:
            logger.info(f"🖼️ Imagen detectada: {url[:50]}...")
            return False, url
    
    return False, ""

def get_account_id(auth_header: dict) -> str:
    """
    Obtiene el account ID de Google Business Profile.
    
    Args:
        auth_header: Header de autorización
        
    Returns:
        Account ID en formato accounts/XXXXX
    """
    global _cached_account_id
    
    if _cached_account_id:
        return _cached_account_id
    
    try:
        url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
        response = requests.get(url, headers=auth_header, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        accounts = data.get("accounts", [])
        
        if accounts:
            # Tomar la primera cuenta disponible
            _cached_account_id = accounts[0].get("name", "")
            logger.info(f"Account ID obtenido: {_cached_account_id}")
            return _cached_account_id
        else:
            raise ValueError("No se encontraron cuentas GBP")
            
    except Exception as e:
        logger.error(f"Error obteniendo account ID: {e}")
        raise

def fix_location_format(location_name: str, auth_header: dict) -> str:
    """
    Corrige el formato de location_name si está incompleto.
    
    Args:
        location_name: Nombre de ubicación (puede estar incompleto)
        auth_header: Header de autorización
        
    Returns:
        Nombre de ubicación en formato correcto: accounts/XXXX/locations/YYYY
    """
    # Si ya tiene el formato correcto, no hacer nada
    if location_name.startswith("accounts/"):
        return location_name
    
    # Si está en formato incompleto, corregir
    if location_name.startswith("locations/"):
        account_id = get_account_id(auth_header)
        corrected_name = f"{account_id}/{location_name}"
        logger.info(f"Corrigiendo formato: {location_name} -> {corrected_name}")
        return corrected_name
    
    # Si no reconocemos el formato, devolver tal como está
    logger.warning(f"Formato de ubicación no reconocido: {location_name}")
    return location_name


def create_local_post(
    location_name: str,
    auth_header: dict,
    summary: str,
    media_url: Optional[str] = None,
    call_to_action: Optional[dict] = None,
    video_local: Optional[str] = None,
    imagen_local: Optional[str] = None,
    imagen_url: Optional[str] = None
) -> dict:
    """
    Crea un post local en Google Business Profile usando la API v4 oficial.
    Maneja automáticamente videos (Media Gallery) e imágenes (additional_photo_urls).
    
    Args:
        location_name: Nombre completo de la locación (formato: accounts/*/locations/*)
        auth_header: Dict con header Authorization
        summary: Texto del post (máximo 1500 caracteres)
        media_url: URL de la imagen (opcional - para compatibilidad)
        call_to_action: Dict con acción de llamada (opcional)
        video_local: URL del video en Supabase (prioridad máxima)
        imagen_local: URL de imagen en Supabase
        imagen_url: URL original de imagen/video
        
    Returns:
        Response de la API con datos del post creado
        
    Raises:
        requests.exceptions.HTTPError: Si la API retorna error
    """
    # Corregir formato de location_name si es necesario
    corrected_location = fix_location_format(location_name, auth_header)
    
    # Detectar tipo de contenido (video vs imagen)
    es_video, final_media_url = detect_video_content(video_local, imagen_local, imagen_url)
    
    # Si no hay final_media_url, usar media_url como fallback
    if not final_media_url and media_url:
        # Verificar si media_url es video
        es_video_fallback, _ = detect_video_content(None, None, media_url)
        if es_video_fallback:
            es_video, final_media_url = True, media_url
        else:
            final_media_url = media_url
    
    # MANEJAR VIDEOS: subir a Media Gallery (NO a localPosts)
    if es_video and final_media_url:
        logger.info(f"🎥 DETECTADO VIDEO -> enviando a GBP Media Gallery")
        try:
            # Extraer account_id de corrected_location
            account_id = corrected_location.split('/locations/')[0]
            location_id = corrected_location.split('/')[-1]
            
            video_media_result = gbp_media_create_video(
                account_id=account_id,
                location_id=f"locations/{location_id}",
                video_url=final_media_url,
                auth_header=auth_header
            )
            
            # Crear un post de texto con referencia al video subido
            logger.info(f"📝 Creando post de texto (video ya en galería)")
            payload = {
                "languageCode": "es",
                "summary": summary[:1500],
                "topicType": "STANDARD"
            }
            
            # No agregar media al post, el video ya está en la galería
            
        except Exception as e:
            logger.error(f"❌ Error subiendo video a galería: {e}")
            # Fallback: crear post solo con texto
            payload = {
                "languageCode": "es",
                "summary": summary[:1500],
                "topicType": "STANDARD"
            }
    else:
        # MANEJAR IMÁGENES: flujo normal con additional_photo_urls
        logger.info(f"🖼️ DETECTADO IMAGEN -> usando additional_photo_urls")
        payload = {
            "languageCode": "es",
            "summary": summary[:1500],
            "topicType": "STANDARD"
        }
        
        # Agregar imagen si existe
        if final_media_url:
            payload["media"] = [{
                "mediaFormat": "PHOTO",
                "sourceUrl": final_media_url
            }]
    
    # Agregar call to action si existe
    if call_to_action:
        payload["callToAction"] = call_to_action
    
    # API oficial de Google My Business v4 (documentación 2024)
    base_url = "https://mybusiness.googleapis.com/v4"
    url = f"{base_url}/{corrected_location}/localPosts"
    
    try:
        logger.info(f"📮 Creando localPost en GBP...")
        response = requests.post(url, headers=auth_header, json=payload)
        response.raise_for_status()
        
        data = response.json()
        tipo_contenido = "🎥 VIDEO" if es_video else "🖼️ IMAGEN"
        logger.info(f"✅ Post creado exitosamente ({tipo_contenido}) en {location_name}: {data.get('name', 'N/A')}")
        
        # Si es video, agregar info del media a la respuesta
        if es_video and 'video_media_result' in locals():
            data['_video_media_info'] = video_media_result
        
        return data
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP error creando post en {location_name}: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error creando post en {location_name}: {e}")
        raise


def list_local_posts(location_name: str, auth_header: dict, page_size: int = 50) -> list[dict]:
    """
    Lista posts locales de una locación usando GBP API v4.
    
    Args:
        location_name: Nombre completo de la locación (formato: accounts/*/locations/*)
        auth_header: Dict con header Authorization
        page_size: Tamaño de página (default 50)
        
    Returns:
        Lista de posts en formato raw de la API
    """
    # Corregir formato de location_name si es necesario
    corrected_location = fix_location_format(location_name, auth_header)
    
    base_url = "https://mybusiness.googleapis.com/v4"
    url = f"{base_url}/{corrected_location}/localPosts"
    
    params = {
        "pageSize": page_size
    }
    
    all_posts = []
    page_token = None
    
    try:
        while True:
            if page_token:
                params["pageToken"] = page_token
            
            response = requests.get(url, headers=auth_header, params=params)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("localPosts", [])
            all_posts.extend(posts)
            
            logger.debug(f"Posts obtenidos en esta página: {len(posts)}")
            
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        
        logger.info(f"Total posts obtenidos para {location_name}: {len(all_posts)}")
        return all_posts
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error listando posts de {location_name}: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listando posts de {location_name}: {e}")
        raise


def delete_local_post(post_name: str, auth_header: dict) -> None:
    """
    Elimina un post local de GBP.
    
    Args:
        post_name: Nombre completo del post (formato: accounts/*/locations/*/localPosts/*)
        auth_header: Dict con header Authorization
    """
    base_url = "https://mybusiness.googleapis.com/v4"
    url = f"{base_url}/{post_name}"
    
    try:
        response = requests.delete(url, headers=auth_header)
        response.raise_for_status()
        logger.info(f"Post eliminado exitosamente: {post_name}")
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error eliminando post {post_name}: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error eliminando post {post_name}: {e}")
        raise
