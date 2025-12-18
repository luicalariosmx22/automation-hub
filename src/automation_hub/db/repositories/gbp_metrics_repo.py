"""
Repositorio para la tabla gbp_metrics_daily.
"""
import logging
from supabase import Client

logger = logging.getLogger(__name__)


def upsert_metrics_daily(supabase: Client, rows: list[dict]) -> None:
    """
    Inserta o actualiza métricas diarias en la tabla gbp_metrics_daily.
    Usa (location_name, metric, date) como PK.
    
    Args:
        supabase: Cliente de Supabase
        rows: Lista de diccionarios con datos de métricas
    """
    if not rows:
        logger.info("No hay métricas para insertar")
        return
    
    try:
        response = supabase.table("gbp_metrics_daily").upsert(
            rows,
            on_conflict="location_name,metric,date"
        ).execute()
        
        logger.info(f"Métricas procesadas: {len(rows)}")
    
    except Exception as e:
        logger.error(f"Error haciendo upsert de métricas: {e}")
        raise
