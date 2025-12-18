"""
Repositorio para la tabla gbp_reviews.
"""
import logging
from supabase import Client

logger = logging.getLogger(__name__)


def upsert_reviews(supabase: Client, rows: list[dict]) -> None:
    """
    Inserta o actualiza reviews en la tabla gbp_reviews.
    Usa (location_name, review_id) como constraint único.
    
    Args:
        supabase: Cliente de Supabase
        rows: Lista de diccionarios con datos de reviews
    """
    if not rows:
        logger.info("No hay reviews para insertar")
        return
    
    try:
        response = supabase.table("gbp_reviews").upsert(
            rows,
            on_conflict="location_name,review_id"
        ).execute()
        
        logger.info(f"Reviews procesadas: {len(rows)}")
    
    except Exception as e:
        logger.error(f"Error haciendo upsert de reviews: {e}")
        raise
