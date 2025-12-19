"""
Script para configurar tabla jobs_config con los jobs iniciales.

Uso:
    PYTHONPATH=src python scripts/setup_jobs_config.py
"""
import sys
import logging
from automation_hub.config.logging import setup_logging
from automation_hub.db.supabase_client import create_client_from_env

logger = logging.getLogger(__name__)

# Jobs a configurar con sus intervalos (en minutos)
JOBS_INICIALES = [
    {
        "job_name": "gbp.reviews.daily",
        "enabled": True,
        "schedule_interval_minutes": 1440,  # 24 horas
        "config": {
            "descripcion": "Sincroniza reviews de Google Business Profile",
            "dependencias": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GBP_REFRESH_TOKEN"]
        }
    },
    {
        "job_name": "gbp.metrics.daily",
        "enabled": True,
        "schedule_interval_minutes": 1440,  # 24 horas
        "config": {
            "descripcion": "Sincroniza métricas de Google Business Profile",
            "dependencias": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GBP_REFRESH_TOKEN"]
        }
    },
    {
        "job_name": "meta_ads.rechazos.daily",
        "enabled": True,
        "schedule_interval_minutes": 1440,  # 24 horas
        "config": {
            "descripcion": "Detecta y alerta sobre anuncios rechazados en Meta Ads",
            "dependencias": ["SUPABASE_URL", "SUPABASE_KEY"]
        }
    }
]


def setup_jobs():
    """Inserta/actualiza configuración inicial de jobs."""
    setup_logging()
    logger.info("Configurando jobs en tabla jobs_config")
    
    try:
        supabase = create_client_from_env()
        
        for job_data in JOBS_INICIALES:
            job_name = job_data["job_name"]
            logger.info(f"Configurando job: {job_name}")
            
            # Upsert (inserta o actualiza)
            result = (
                supabase.table("jobs_config")
                .upsert(
                    {
                        **job_data,
                        "next_run_at": "now()"  # Ejecutar inmediatamente en la primera corrida
                    },
                    on_conflict="job_name"
                )
                .execute()
            )
            
            if result.data:
                logger.info(f"✓ Job {job_name} configurado")
            else:
                logger.warning(f"⚠️  No se pudo confirmar configuración de {job_name}")
        
        logger.info("=== Configuración completada ===")
        
        # Mostrar estado final
        result = (
            supabase.table("jobs_config")
            .select("job_name, enabled, schedule_interval_minutes, next_run_at")
            .order("job_name")
            .execute()
        )
        
        if result.data:
            logger.info("\nJobs configurados:")
            for job in result.data:
                status = "✓ Habilitado" if job["enabled"] else "✗ Deshabilitado"
                interval = job["schedule_interval_minutes"]
                next_run = job.get("next_run_at", "No programado")
                logger.info(f"  • {job['job_name']}: {status}, cada {interval}min, próx: {next_run}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error configurando jobs: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(setup_jobs())
