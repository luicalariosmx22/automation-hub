"""
Runner CLI para ejecutar jobs en automation-hub.

Uso:
    python -m automation_hub.runners.run_job <job_name>
"""
import logging
import sys
from automation_hub.config.logging import setup_logging
from automation_hub.jobs.registry import get_job, list_jobs

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Punto de entrada principal del runner.
    
    Returns:
        Exit code: 0 éxito, 1 error en ejecución, 2 job no encontrado
    """
    setup_logging()
    
    # Validar argumentos
    if len(sys.argv) < 2:
        logger.error("Uso: python -m automation_hub.runners.run_job <job_name>")
        _print_available_jobs()
        return 2
    
    job_name = sys.argv[1]
    
    # Buscar job en el registro
    job_func = get_job(job_name)
    
    if job_func is None:
        logger.error(f"Job '{job_name}' no encontrado")
        _print_available_jobs()
        return 2
    
    # Ejecutar job
    try:
        logger.info(f"Iniciando ejecución del job: {job_name}")
        job_func()
        logger.info(f"Job '{job_name}' completado exitosamente")
        return 0
    except Exception as e:
        logger.exception(f"Error ejecutando job '{job_name}': {e}")
        return 1


def _print_available_jobs() -> None:
    """Imprime la lista de jobs disponibles."""
    jobs = list_jobs()
    
    if not jobs:
        logger.info("No hay jobs registrados actualmente")
        logger.info("Para registrar un job, usa: register_job(name, callable)")
    else:
        logger.info("Jobs disponibles:")
        for job in jobs:
            logger.info(f"  - {job}")


if __name__ == "__main__":
    sys.exit(main())
