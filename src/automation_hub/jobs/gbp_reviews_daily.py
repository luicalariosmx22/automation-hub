"""
Job para sincronizar reviews diarias de Google Business Profile.
"""
import logging
import os
from automation_hub.integrations.google.oauth import get_bearer_token
from automation_hub.integrations.gbp.reviews_v4 import list_all_reviews, map_review_to_row
from automation_hub.db.supabase_client import create_client
from automation_hub.db.repositories.gbp_locations_repo import fetch_active_locations
from automation_hub.db.repositories.gbp_reviews_repo import upsert_reviews

logger = logging.getLogger(__name__)

JOB_NAME = "gbp.reviews.daily"


def run(ctx=None):
    """
    Ejecuta el job de sincronización de reviews diarias.
    
    1. Obtiene token de acceso de Google
    2. Lee locaciones activas de Supabase
    3. Para cada locación, descarga reviews
    4. Inserta/actualiza reviews en BD
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Cargar configuración desde env vars
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GBP_REFRESH_TOKEN")
    nombre_nora = os.getenv("GBP_NOMBRE_NORA")  # Opcional
    
    # Validar variables requeridas
    required_vars = {
        "SUPABASE_URL": supabase_url,
        "SUPABASE_KEY": supabase_key,
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret,
        "GBP_REFRESH_TOKEN": refresh_token
    }
    
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        raise ValueError(f"Variables de entorno faltantes: {', '.join(missing_vars)}")
    
    # Obtener token de acceso
    logger.info("Obteniendo token de acceso de Google")
    token = get_bearer_token(client_id, client_secret, refresh_token)
    
    # Crear cliente Supabase
    supabase = create_client(supabase_url, supabase_key)
    
    # Obtener locaciones activas
    logger.info("Obteniendo locaciones activas")
    locations = fetch_active_locations(supabase, nombre_nora)
    
    if not locations:
        logger.warning("No se encontraron locaciones activas")
        return
    
    # Procesar cada locación
    total_reviews = 0
    batch_size = 200
    
    for location in locations:
        location_name = location.get("location_name")
        nombre_nora_loc = location.get("nombre_nora")
        api_id = location.get("api_id")
        
        if not location_name:
            logger.warning(f"Locación sin location_name: {location}")
            continue
        
        try:
            logger.info(f"Procesando reviews para: {location_name}")
            
            # Descargar reviews
            reviews_raw = list_all_reviews(location_name, token)
            
            if not reviews_raw:
                logger.info(f"No hay reviews para {location_name}")
                continue
            
            # Mapear reviews a formato de BD
            reviews_mapped = [
                map_review_to_row(review, nombre_nora_loc, api_id, location_name)
                for review in reviews_raw
            ]
            
            # Insertar por batches
            for i in range(0, len(reviews_mapped), batch_size):
                batch = reviews_mapped[i:i + batch_size]
                upsert_reviews(supabase, batch)
            
            total_reviews += len(reviews_mapped)
            logger.info(f"Reviews procesadas para {location_name}: {len(reviews_mapped)}")
        
        except Exception as e:
            logger.error(f"Error procesando {location_name}: {e}", exc_info=True)
            # Continuar con la siguiente locación
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Total reviews: {total_reviews}")
