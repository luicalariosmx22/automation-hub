"""
Repository para la tabla meta_ads_cuentas.
"""
import logging
from typing import List, Dict, Any, Optional, cast
from supabase import Client

logger = logging.getLogger(__name__)


def fetch_cuentas_activas(
    supabase: Client,
    nombre_nora: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene las cuentas publicitarias activas.
    
    Args:
        supabase: Cliente de Supabase
        nombre_nora: Filtro opcional por tenant
        
    Returns:
        Lista de cuentas publicitarias activas
    """
    query = (
        supabase.table("meta_ads_cuentas")
        .select("*")
        .eq("activo", True)
    )
    
    if nombre_nora:
        query = query.eq("nombre_nora", nombre_nora)
    
    result = query.execute()
    return cast(List[Dict[str, Any]], result.data)


def actualizar_cuenta(
    supabase: Client,
    cuenta_id: str,
    datos: Dict[str, Any]
) -> None:
    """
    Actualiza información de una cuenta publicitaria.
    
    Args:
        supabase: Cliente de Supabase
        cuenta_id: ID de la cuenta publicitaria
        datos: Diccionario con campos a actualizar
    """
    try:
        # Agregar timestamp de actualización
        datos["actualizada_en"] = "now()"
        
        result = (
            supabase.table("meta_ads_cuentas")
            .update(datos)
            .eq("id_cuenta_publicitaria", cuenta_id)
            .execute()
        )
        
        if result.data:
            logger.info(f"Cuenta {cuenta_id} actualizada correctamente")
        else:
            logger.warning(f"No se pudo actualizar cuenta {cuenta_id}")
    
    except Exception as e:
        logger.error(f"Error actualizando cuenta {cuenta_id}: {e}")
        raise


def marcar_error_cuenta(
    supabase: Client,
    cuenta_id: str,
    error_mensaje: str,
    error_detalles: Optional[Dict[str, Any]] = None
) -> None:
    """
    Marca una cuenta con error y guarda detalles.
    
    Args:
        supabase: Cliente de Supabase
        cuenta_id: ID de la cuenta publicitaria
        error_mensaje: Mensaje de error
        error_detalles: Detalles adicionales del error
    """
    datos_error = {
        "conectada": False,
        "ultimo_error": {
            "mensaje": error_mensaje,
            "detalles": error_detalles or {},
            "timestamp": "now()"
        },
        "ultimo_error_at": "now()",
        "actualizada_en": "now()"
    }
    
    try:
        supabase.table("meta_ads_cuentas").update(datos_error).eq(
            "id_cuenta_publicitaria", cuenta_id
        ).execute()
        
        logger.warning(f"Cuenta {cuenta_id} marcada con error: {error_mensaje}")
    
    except Exception as e:
        logger.error(f"Error marcando error en cuenta {cuenta_id}: {e}")
