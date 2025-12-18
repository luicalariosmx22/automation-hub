"""
Repositorio para la tabla gbp_locations.
"""
import logging
from typing import Optional
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
            "nombre_nora, api_id, location_name, location_id"
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
