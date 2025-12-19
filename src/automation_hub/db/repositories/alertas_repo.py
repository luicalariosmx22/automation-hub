"""
Repositorio para tabla alertas.
"""
import logging
from typing import Optional, Dict, Any
from supabase import Client

logger = logging.getLogger(__name__)


def crear_alerta(
    supabase: Client,
    nombre: str,
    tipo: str,
    nombre_nora: str,
    descripcion: Optional[str] = None,
    evento_origen: Optional[str] = None,
    datos: Optional[Dict[str, Any]] = None,
    prioridad: str = "media"
) -> None:
    """
    Crea una alerta en la tabla alertas.
    
    Args:
        supabase: Cliente de Supabase
        nombre: Nombre de la alerta
        tipo: Tipo de alerta
        nombre_nora: Nombre de la Nora asociada
        descripcion: Descripción de la alerta
        evento_origen: Evento que originó la alerta
        datos: Datos adicionales en formato JSON
        prioridad: Prioridad (baja, media, alta)
    """
    alerta = {
        "nombre": nombre,
        "tipo": tipo,
        "nombre_nora": nombre_nora,
        "prioridad": prioridad,
        "activa": True,
        "vista": False,
        "resuelta": False
    }
    
    if descripcion:
        alerta["descripcion"] = descripcion
    if evento_origen:
        alerta["evento_origen"] = evento_origen
    if datos:
        alerta["datos"] = datos
    
    try:
        supabase.table("alertas").insert(alerta).execute()
        logger.info(f"Alerta creada: {nombre}")
    except Exception as e:
        logger.error(f"Error creando alerta: {e}", exc_info=True)
        raise
