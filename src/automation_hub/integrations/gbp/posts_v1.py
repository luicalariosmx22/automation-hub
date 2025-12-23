"""
Cliente para Google Business Profile Local Posts API v1.
"""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


def create_local_post(
    location_name: str,
    auth_header: dict,
    summary: str,
    media_url: Optional[str] = None,
    call_to_action: Optional[dict] = None
) -> dict:
    """
    Crea un post local en Google Business Profile usando la API v4.13.
    
    Args:
        location_name: Nombre completo de la locación (formato: accounts/*/locations/*)
        auth_header: Dict con header Authorization
        summary: Texto del post (máximo 1500 caracteres)
        media_url: URL de la imagen (opcional)
        call_to_action: Dict con acción de llamada (opcional)
        
    Returns:
        Response de la API con datos del post creado
        
    Raises:
        requests.exceptions.HTTPError: Si la API retorna error
    """
    base_url = "https://mybusiness.googleapis.com/v4"
    url = f"{base_url}/{location_name}/localPosts"
    
    # Construir payload
    payload = {
        "languageCode": "es",
        "summary": summary[:1500],  # Truncar a 1500 caracteres
        "topicType": "STANDARD"
    }
    
    # Agregar media si existe
    if media_url:
        payload["media"] = [{
            "mediaFormat": "PHOTO",
            "sourceUrl": media_url
        }]
    
    # Agregar call to action si existe
    if call_to_action:
        payload["callToAction"] = call_to_action
    
    try:
        response = requests.post(url, headers=auth_header, json=payload)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Post creado exitosamente en {location_name}: {data.get('name', 'N/A')}")
        return data
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error creando post en {location_name}: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creando post en {location_name}: {e}")
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
    base_url = "https://mybusiness.googleapis.com/v4"
    url = f"{base_url}/{location_name}/localPosts"
    
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
