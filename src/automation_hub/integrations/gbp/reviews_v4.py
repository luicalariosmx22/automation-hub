"""
Cliente para Google Business Profile Reviews API v4.
"""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


def list_all_reviews(parent_location_name: str, auth_header: dict) -> list[dict]:
    """
    Lista todas las reviews de una locación usando GBP API v4.
    Maneja paginación automáticamente.
    
    Args:
        parent_location_name: Nombre completo de la locación (formato: accounts/*/locations/*)
        auth_header: Dict con header Authorization
        
    Returns:
        Lista de reviews en formato raw de la API
    """
    base_url = "https://mybusiness.googleapis.com/v4"
    url = f"{base_url}/{parent_location_name}/reviews"
    
    params = {
        "pageSize": 50,
        "orderBy": "updateTime desc"
    }
    
    all_reviews = []
    page_token = None
    
    try:
        while True:
            if page_token:
                params["pageToken"] = page_token
            
            response = requests.get(url, headers=auth_header, params=params)
            response.raise_for_status()
            
            data = response.json()
            reviews = data.get("reviews", [])
            all_reviews.extend(reviews)
            
            logger.debug(f"Reviews obtenidas en esta página: {len(reviews)}")
            
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        
        logger.info(f"Total reviews obtenidas para {parent_location_name}: {len(all_reviews)}")
        return all_reviews
    
    except requests.exceptions.HTTPError as e:
        # 404 es común (sin acceso a Reviews API v4)
        if e.response.status_code == 404:
            logger.debug(f"Locación {parent_location_name} sin acceso a Reviews API (404)")
        else:
            logger.error(f"HTTP error obteniendo reviews para {parent_location_name}: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error obteniendo reviews para {parent_location_name}: {e}")
        raise


def map_review_to_row(
    review_json: dict,
    nombre_nora: str,
    api_id: str | None,
    location_name: str | None
) -> dict:
    """
    Mapea un review de la API v4 a una fila de base de datos.
    
    Args:
        review_json: Review en formato raw de la API
        nombre_nora: Tenant de la locación
        api_id: ID de la API de la locación
        location_name: Nombre de la locación
        
    Returns:
        Diccionario con datos mapeados para insertar en BD
    """
    # Extraer review_id
    review_id = review_json.get("reviewId")
    if not review_id and "name" in review_json:
        # Si no existe reviewId, derivar del name (último segmento)
        review_id = review_json["name"].split("/")[-1]
    
    # Mapear star rating
    star_rating_map = {
        "ONE": 1,
        "TWO": 2,
        "THREE": 3,
        "FOUR": 4,
        "FIVE": 5
    }
    star_rating_str = review_json.get("starRating")
    star_rating = star_rating_map.get(star_rating_str) if star_rating_str else None
    
    # Extraer reviewer info
    reviewer = review_json.get("reviewer", {})
    reviewer_name = reviewer.get("displayName")
    reviewer_profile_photo_url = reviewer.get("profilePhotoUrl")
    
    # Extraer comentario y respuesta
    comment = review_json.get("comment")
    review_reply = review_json.get("reviewReply", {})
    reply_comment = review_reply.get("comment")
    reply_update_time = review_reply.get("updateTime")
    
    return {
        "nombre_nora": nombre_nora,
        "api_id": api_id,
        "location_name": location_name,
        "review_id": review_id,
        "star_rating": star_rating,
        "comment": comment,
        "reviewer_name": reviewer_name,
        "reviewer_profile_photo_url": reviewer_profile_photo_url,
        "create_time": review_json.get("createTime"),
        "update_time": review_json.get("updateTime"),
        "reply_comment": reply_comment,
        "reply_update_time": reply_update_time,
        "language_code": review_json.get("languageCode"),
        "raw": review_json
    }
