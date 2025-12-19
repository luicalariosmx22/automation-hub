"""
Runner batch para ejecutar múltiples jobs en secuencia.

Uso:
    python -m automation_hub.runners.run_batch
    
Variables de entorno:
    JOB_LIST: Lista de jobs separados por coma (ej: job1,job2,job3)
    JOB_GROUP: Grupo predefinido (tenmin, hourly, daily)
    FAIL_FAST: Si es true, detiene al primer error (default: false)
"""
import logging
import os
import sys
from automation_hub.config.logging import setup_logging
from automation_hub.jobs.registry import get_job, list_jobs

logger = logging.getLogger(__name__)

# Grupos predefinidos de jobs
JOB_GROUPS = {
    "tenmin": [],  # Jobs que corren cada 10 minutos
    "hourly": [],  # Jobs que corren cada hora
    "daily": [     # Jobs que corren una vez al día
        "gbp.reviews.daily",
        "gbp.metrics.daily"
    ]
}


def parse_job_list() -> list[str]:
    """
    Obtiene la lista de jobs a ejecutar desde variables de entorno.
    
    Prioridad:
    1. JOB_LIST (csv)
    2. JOB_GROUP (mapeo a grupo predefinido)
    
    Returns:
        Lista de nombres de jobs a ejecutar
    """
    job_list_str = os.getenv("JOB_LIST")
    if job_list_str:
        jobs = [j.strip() for j in job_list_str.split(",") if j.strip()]
        logger.info(f"Jobs desde JOB_LIST: {jobs}")
        return jobs
    
    job_group = os.getenv("JOB_GROUP")
    if job_group:
        jobs = JOB_GROUPS.get(job_group, [])
        logger.info(f"Jobs desde JOB_GROUP '{job_group}': {jobs}")
        return jobs
    
    logger.warning("No se especificó JOB_LIST ni JOB_GROUP")
    return []


def run_batch() -> int:
    """
    Ejecuta un batch de jobs en secuencia.
    
    Returns:
        Exit code: 0 todos OK, 1 alguno falló, 2 lista vacía o job no existe
    """
    setup_logging()
    logger.info("=== Iniciando ejecución batch ===")
    
    # Obtener lista de jobs
    jobs_to_run = parse_job_list()
    
    if not jobs_to_run:
        logger.error("Lista de jobs vacía. Define JOB_LIST o JOB_GROUP")
        available_jobs = list_jobs()
        if available_jobs:
            logger.info(f"Jobs disponibles: {', '.join(available_jobs)}")
        return 2
    
    # Validar que todos los jobs existen
    missing_jobs = []
    for job_name in jobs_to_run:
        if get_job(job_name) is None:
            missing_jobs.append(job_name)
    
    if missing_jobs:
        logger.error(f"Jobs no encontrados: {', '.join(missing_jobs)}")
        available_jobs = list_jobs()
        if available_jobs:
            logger.info(f"Jobs disponibles: {', '.join(available_jobs)}")
        return 2
    
    # Configuración
    fail_fast = os.getenv("FAIL_FAST", "false").lower() == "true"
    logger.info(f"FAIL_FAST: {fail_fast}")
    
    # Ejecutar jobs
    results = {
        "total": len(jobs_to_run),
        "success": 0,
        "failed": 0,
        "failures": []
    }
    
    for job_name in jobs_to_run:
        logger.info(f"--- Ejecutando job: {job_name} ---")
        job_func = get_job(job_name)
        
        try:
            job_func()
            results["success"] += 1
            logger.info(f"✓ Job '{job_name}' completado exitosamente")
        
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(job_name)
            logger.error(f"✗ Job '{job_name}' falló: {e}", exc_info=True)
            
            if fail_fast:
                logger.error("FAIL_FAST activado, deteniendo ejecución")
                break
    
    # Resumen final
    logger.info("=== Resumen de ejecución batch ===")
    logger.info(f"Total jobs: {results['total']}")
    logger.info(f"Exitosos: {results['success']}")
    logger.info(f"Fallidos: {results['failed']}")
    
    if results["failures"]:
        logger.error(f"Jobs que fallaron: {', '.join(results['failures'])}")
    
    # Determinar exit code
    if results["failed"] > 0:
        logger.error("Ejecución batch completada con errores")
        return 1
    
    logger.info("Ejecución batch completada exitosamente")
    return 0


def main() -> int:
    """Punto de entrada principal."""
    try:
        return run_batch()
    except Exception as e:
        logger.exception(f"Error crítico en run_batch: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
