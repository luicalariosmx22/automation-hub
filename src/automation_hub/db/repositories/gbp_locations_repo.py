"""
Repositorio para la tabla gbp_locations.
"""
import logging
from typing import Optional, Dict
from supabase import Client

logger = logging.getLogger(__name__)


def fetch_active_locations(
    supabase: Client, 
    nombre_nora: Optional[str] = None
) -> list[dict]:
    """
    Obtiene las locaciones activas de GBP desde la base de datos.
    
    Args:
        supabase: Cliente de Supabase
        nombre_nora: Filtro opcional por tenant
        
    Returns:
        Lista de diccionarios con datos de locaciones activas
    """
    try:
        query = supabase.table("gbp_locations").select(
            "nombre_nora, api_id, account_name, location_name, location_id, title"
        ).eq("activa", True)

        if nombre_nora:
            query = query.eq("nombre_nora", nombre_nora)
        
        response = query.execute()
        
        locations = response.data if response.data else []
        logger.info(f"Locaciones activas encontradas: {len(locations)}")
        
        return locations
    
    except Exception as e:
        logger.error(f"Error obteniendo locaciones activas: {e}")
        raise


def get_last_review_sync_times(supabase: Client) -> Dict[str, str]:
    """
    Obtiene la última fecha de sincronización de reviews por ubicación.
    
    Args:
        supabase: Cliente de Supabase
        
    Returns:
        Dict donde key=location_name y value=última fecha ISO de update_time
    """
    try:
        # Paginación manual para traer todas las reviews (supabase limita resultados por request)
        page_size = 1000  # límite típico de PostgREST
        start = 0
        last_times: Dict[str, str] = {}

        while True:
            # Traer un rango
            reviews_response = supabase.table("gbp_reviews").select(
                "location_name, update_time"
            ).range(start, start + page_size - 1).execute()

            data = reviews_response.data or []

            if not data:
                break

            # Agrupar manualmente y encontrar el máximo update_time por location
            for review in data:
                location_name = review.get("location_name")
                update_time = review.get("update_time")

                if location_name and update_time:
                    if location_name not in last_times or update_time > last_times[location_name]:
                        last_times[location_name] = update_time

            # Si vino menos de page_size, ya no hay más páginas
            if len(data) < page_size:
                break

            start += page_size

        if not last_times:
            logger.info("No hay reviews en la base de datos")
            return {}

        logger.info(f"Últimas fechas de sync obtenidas para {len(last_times)} ubicaciones")
        return last_times
    
    except Exception as e:
        logger.error(f"Error obteniendo últimas fechas de sync: {e}")
        return {}  # Retorna dict vacío para sincronizar todo
