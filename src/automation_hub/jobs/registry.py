"""
Registro de jobs disponibles en automation-hub.
"""
import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Registro global de jobs
_JOB_REGISTRY: Dict[str, Callable] = {}


def register_job(name: str, job_func: Callable) -> None:
    """
    Registra un job en el sistema.
    
    Args:
        name: Nombre único del job
        job_func: Función callable que implementa el job
    """
    if name in _JOB_REGISTRY:
        logger.warning(f"Job '{name}' ya existe en el registro, será sobrescrito")
    
    _JOB_REGISTRY[name] = job_func
    logger.debug(f"Job '{name}' registrado exitosamente")


def get_job(name: str) -> Optional[Callable]:
    """
    Obtiene un job del registro.
    
    Args:
        name: Nombre del job a buscar
        
    Returns:
        La función del job si existe, None si no existe
    """
    return _JOB_REGISTRY.get(name)


def list_jobs() -> List[str]:
    """
    Lista todos los jobs registrados.
    
    Returns:
        Lista con los nombres de todos los jobs disponibles
    """
    return sorted(_JOB_REGISTRY.keys())


def _register_default_jobs():
    """Registra los jobs por defecto del sistema."""
    try:
        from automation_hub.jobs import (
            gbp_reviews_daily,
            gbp_metrics_daily,
            meta_ads_rechazos_daily,
            meta_ads_cuentas_sync_daily,
            calendar_sync,
            calendar_daily_summary,
            meta_ads_daily_sync,
            meta_ads_weekly_report
        )
        
        register_job("gbp.reviews.daily", gbp_reviews_daily.run)
        register_job("gbp.metrics.daily", gbp_metrics_daily.run)
        register_job("meta_ads.rechazos.daily", meta_ads_rechazos_daily.run)
        register_job("meta_ads.cuentas.sync.daily", meta_ads_cuentas_sync_daily.run)
        register_job("calendar.sync", calendar_sync.run)
        register_job("calendar.daily.summary", calendar_daily_summary.run)
        register_job("meta_ads.daily.sync", meta_ads_daily_sync.run)
        register_job("meta_ads.weekly.report", meta_ads_weekly_report.run)
    except ImportError as e:
        logger.warning(f"No se pudieron importar algunos jobs: {e}")


# Registrar jobs al importar el módulo
_register_default_jobs()
