"""
Job para sincronizar métricas diarias de Google Business Profile.
"""
import logging
import os
from datetime import date, timedelta
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.performance_v1 import fetch_multi_daily_metrics, parse_metrics_to_rows
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.gbp_locations_repo import fetch_active_locations
from automation_hub.db.repositories.gbp_metrics_repo import upsert_metrics_daily
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram, TelegramNotifier

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
    total_metrics = 0
    
    for location in locations:
        location_name = location.get("location_name")  # Ya es locations/{id}
        nombre_nora_loc = location.get("nombre_nora") or "Sistema"
        api_id = location.get("api_id")  # Puede ser None si no existe
        
        if not location_name:
            logger.warning(f"Locación sin location_name: {location}")
            continue
        
        try:
            logger.info(f"Procesando métricas para: {location_name}")
            
            # Descargar métricas
            time_series = fetch_multi_daily_metrics(
                location_name, auth_header, metrics, start_date, end_date
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
            # 404 es normal (locación sin acceso a Performance API)
            if "404" in str(e):
                logger.warning(f"Locación {location_name} sin acceso a Performance API (404)")
            else:
                logger.error(f"Error procesando {location_name}: {e}", exc_info=True)
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Total métricas: {total_metrics}")
    
    # Crear alerta de job completado y notificar por Telegram
    try:
        crear_alerta(
            supabase=supabase,
            nombre=f"Métricas GBP Actualizadas",
            tipo="job_completado",
            nombre_nora="Sistema",
            descripcion=f"Se han sincronizado {total_metrics} métricas de {len(locations)} locaciones GBP (últimos {days_back} días)",
            evento_origen=JOB_NAME,
            datos={
                "total_metricas": total_metrics,
                "total_locaciones": len(locations),
                "dias_atras": days_back,
                "fecha_inicio": str(start_date),
                "fecha_fin": str(end_date),
                "job_name": JOB_NAME
            },
            prioridad="baja"
        )
        
        # Notificar por Telegram usando bot de notificaciones
        bot_token = "8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE"
        chat_id = "5674082622"
        notifier = TelegramNotifier(bot_token=bot_token, default_chat_id=chat_id)
        
        notifier.enviar_alerta(
            nombre="📊 Métricas GBP Sincronizadas",
            descripcion=f"Job completado exitosamente",
            prioridad="baja",
            datos={
                "Total Métricas": total_metrics,
                "Locaciones": len(locations),
                "Período": f"{days_back} días"
            }
        )
    except Exception as e:
        logger.warning(f"No se pudo crear alerta: {e}")
