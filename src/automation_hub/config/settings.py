"""
Configuración de settings para automation-hub.
Carga variables de entorno sin validación.
"""
import os
from typing import Any, Dict


def load_settings() -> Dict[str, Any]:
    """
    Carga la configuración desde variables de entorno.
    
    Returns:
        Dict con la configuración del sistema.
    """
    return {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timezone": os.getenv("TZ", "UTC"),
        # Agregar más variables según necesidad
    }
