"""
Configuración de logging para automation-hub.
"""
import logging
import os
import sys


def setup_logging() -> None:
    """
    Configura el logging del sistema.
    Nivel de log controlado por variable de entorno LOG_LEVEL.
    Default: INFO
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Validar nivel de log
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Configurar formato
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configurar logging
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("automation_hub")
    logger.info(f"Logging configurado con nivel: {log_level}")
