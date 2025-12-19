"""
Repository para gestionar configuración de jobs.
"""
import logging
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


def fetch_jobs_pendientes(supabase: Client) -> List[Dict[str, Any]]:
    """
    Obtiene jobs habilitados que están listos para ejecutar.
    
    Filtra por:
    - enabled = true
    - next_run_at <= NOW() OR next_run_at IS NULL
    
    Returns:
        Lista de jobs listos para ejecutar
    """
    result = (
        supabase.table("jobs_config")
        .select("*")
        .eq("enabled", True)
        .or_("next_run_at.lte.now(),next_run_at.is.null")
        .order("job_name")
        .execute()
    )
    return cast(List[Dict[str, Any]], result.data)


def marcar_job_ejecutado(
    supabase: Client, 
    job_name: str,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    Marca un job como ejecutado actualizando last_run_at.
    
    El trigger de BD calculará next_run_at automáticamente basado en schedule_interval_minutes.
    
    Args:
        supabase: Cliente de Supabase
        job_name: Nombre del job
        success: Si la ejecución fue exitosa
        error_message: Mensaje de error (si hubo)
    """
    update_data: Dict[str, Any] = {
        "last_run_at": datetime.utcnow().isoformat()
    }
    
    # Guardar info de error si hubo
    if not success and error_message:
        update_data["config"] = {
            "last_error": error_message,
            "last_error_at": datetime.utcnow().isoformat()
        }
    
    result = (
        supabase.table("jobs_config")
        .update(update_data)
        .eq("job_name", job_name)
        .execute()
    )
    
    if result.data:
        logger.info(f"Job {job_name} marcado como ejecutado")
    else:
        logger.warning(f"No se pudo actualizar estado del job {job_name}")


def get_job_config(supabase: Client, job_name: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene la configuración de un job específico.
    
    Args:
        supabase: Cliente de Supabase
        job_name: Nombre del job
        
    Returns:
        Configuración del job o None si no existe
    """
    result = (
        supabase.table("jobs_config")
        .select("*")
        .eq("job_name", job_name)
        .single()
        .execute()
    )
    return result.data if result.data else None


def actualizar_intervalo(
    supabase: Client,
    job_name: str,
    interval_minutes: int
) -> None:
    """
    Actualiza el intervalo de ejecución de un job.
    
    Args:
        supabase: Cliente de Supabase
        job_name: Nombre del job
        interval_minutes: Nuevo intervalo en minutos
    """
    supabase.table("jobs_config").update({
        "schedule_interval_minutes": interval_minutes
    }).eq("job_name", job_name).execute()
    
    logger.info(f"Intervalo de {job_name} actualizado a {interval_minutes} minutos")


def habilitar_deshabilitar_job(
    supabase: Client,
    job_name: str,
    enabled: bool
) -> None:
    """
    Habilita o deshabilita un job.
    
    Args:
        supabase: Cliente de Supabase
        job_name: Nombre del job
        enabled: True para habilitar, False para deshabilitar
    """
    supabase.table("jobs_config").update({
        "enabled": enabled
    }).eq("job_name", job_name).execute()
    
    estado = "habilitado" if enabled else "deshabilitado"
    logger.info(f"Job {job_name} {estado}")
