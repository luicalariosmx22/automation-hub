"""
Job para sincronizar métricas diarias de Google Business Profile.
"""
import logging
import os
from datetime import date, timedelta
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.performance_v1 import fetch_multi_daily_metrics, parse_metrics_to_rows
from automation_hub.db.supabase_client import create_client
from automation_hub.db.repositories.gbp_locations_repo import fetch_active_locations
from automation_hub.db.repositories.gbp_metrics_repo import upsert_metrics_daily

logger = logging.getLogger(__name__)

JOB_NAME = "gbp.metrics.daily"


def run(ctx=None):
    """
    Ejecuta el job de sincronización de métricas diarias.
    
    1. Obtiene token de acceso de Google
    2. Lee locaciones activas de Supabase
    3. Para cada locación con location_id válido, descarga métricas
    4. Inserta/actualiza métricas en BD
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Cargar configuración desde env vars
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    nombre_nora = os.getenv("GBP_NOMBRE_NORA")  # Opcional
    
    # Métricas a descargar
    metrics_csv = os.getenv("GBP_METRICS", "WEBSITE_CLICKS,CALL_CLICKS")
    metrics = [m.strip() for m in metrics_csv.split(",")]
    
    # Rango de días
    days_back = int(os.getenv("GBP_DAYS_BACK", "30"))
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    logger.info(f"Métricas a obtener: {metrics}")
    logger.info(f"Rango de fechas: {start_date} a {end_date}")
    
    # Validar variables requeridas de Supabase
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL y SUPABASE_KEY son requeridos")
    
    # Obtener header de autorización (valida OAuth internamente)
    logger.info("Obteniendo credenciales de Google OAuth")
    auth_header = get_bearer_header()
    
    # Crear cliente Supabase
    supabase = create_client(supabase_url, supabase_key)
    
    # Obtener locaciones activas
    logger.info("Obteniendo locaciones activas")
    locations = fetch_active_locations(supabase, nombre_nora)
    
    if not locations:
        logger.warning("No se encontraron locaciones activas")
        return
    
    # Procesar cada locación
    total_metrics = 0
    
    for location in locations:
        location_id = location.get("location_id")
        location_name = location.get("location_name")
        nombre_nora_loc = location.get("nombre_nora")
        api_id = location.get("api_id")
        
        if not location_id:
            logger.warning(f"Locación sin location_id: {location_name}")
            continue
        
        try:
            logger.info(f"Procesando métricas para: {location_name}")
            
            # Descargar métricas
            time_series = fetch_multi_daily_metrics(
                location_id, auth_header, metrics, start_date, end_date
            )
            
            if not time_series:
                logger.info(f"No hay métricas para {location_name}")
                continue
            
            # Parsear a formato de BD
            metrics_rows = parse_metrics_to_rows(
                time_series, nombre_nora_loc, api_id, location_name
            )
            
            if metrics_rows:
                # Insertar en BD
                upsert_metrics_daily(supabase, metrics_rows)
                total_metrics += len(metrics_rows)
                logger.info(f"Métricas procesadas para {location_name}: {len(metrics_rows)}")
        
        except Exception as e:
            logger.error(f"Error procesando {location_name}: {e}", exc_info=True)
            # Continuar con la siguiente locación
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Total métricas: {total_metrics}")
