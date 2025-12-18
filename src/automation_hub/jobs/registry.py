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
