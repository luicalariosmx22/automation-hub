"""
Job para sincronizar reviews diarias de Google Business Profile.
"""
import logging
import os
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.reviews_v4 import list_all_reviews, map_review_to_row
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.gbp_locations_repo import fetch_active_locations
from automation_hub.db.repositories.gbp_reviews_repo import upsert_reviews
from automation_hub.db.repositories.alertas_repo import crear_alerta

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
    nombre_nora = os.getenv("GBP_NOMBRE_NORA")  # Opcional
    
    # Obtener header de autorización (valida OAuth internamente)
    logger.info("Obteniendo credenciales de Google OAuth")
    auth_header = get_bearer_header()
    
    # Crear cliente Supabase (valida variables internamente)
    supabase = create_client_from_env()
    
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
        location_name = location.get("location_name") or ""
        nombre_nora_loc = location.get("nombre_nora") or "Sistema"
        api_id = location.get("api_id") or ""
        
        if not location_name:
            logger.warning(f"Locación sin location_name: {location}")
            continue
        
        try:
            logger.info(f"Procesando reviews para: {location_name}")
            
            # Descargar reviews
            reviews_raw = list_all_reviews(location_name, auth_header)
            
            if not reviews_raw:
                logger.info(f"No hay reviews para {location_name}")
                continue
            
            # Mapear reviews a formato de BD
            reviews_mapped = [
                map_review_to_row(review, nombre_nora_loc or "", api_id, location_name)
                for review in reviews_raw
            ]
            
            # Insertar por batches
            for i in range(0, len(reviews_mapped), batch_size):
                batch = reviews_mapped[i:i + batch_size]
                upsert_reviews(supabase, batch)
            
            total_reviews += len(reviews_mapped)
            logger.info(f"Reviews procesadas para {location_name}: {len(reviews_mapped)}")
        
        except Exception as e:
            # 404 es normal (locación sin acceso a Reviews API v4)
            if "404" in str(e):
                logger.warning(f"Locación {location_name} sin acceso a Reviews API (404)")
            else:
                logger.error(f"Error procesando {location_name}: {e}", exc_info=True)
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Total reviews: {total_reviews}")
    
    # Crear alerta de job completado
    try:
        crear_alerta(
            supabase=supabase,
            nombre=f"Reviews GBP Actualizadas",
            tipo="job_completado",
            nombre_nora="Sistema",
            descripcion=f"Se han sincronizado {total_reviews} reviews de {len(locations)} locaciones GBP",
            evento_origen=JOB_NAME,
            datos={
                "total_reviews": total_reviews,
                "total_locaciones": len(locations),
                "job_name": JOB_NAME
            },
            prioridad="baja"
        )
    except Exception as e:
        logger.warning(f"No se pudo crear alerta: {e}")
