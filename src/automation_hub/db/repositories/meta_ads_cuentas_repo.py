"""
Repository para la tabla meta_ads_cuentas.
"""
import logging
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
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


def actualizar_estado_cuenta(
    supabase: Client,
    id_cuenta: int,
    account_status: int,
    ads_activos: Optional[int] = None,
    ultimo_error: Optional[Dict[str, Any]] = None
) -> None:
    """
    Actualiza el estado de una cuenta publicitaria.
    
    Args:
        supabase: Cliente de Supabase
        id_cuenta: ID interno de la cuenta (campo 'id')
        account_status: Estado de la cuenta (1=activa, 2=deshabilitada, etc)
        ads_activos: Número de anuncios activos (opcional)
        ultimo_error: Datos del último error si lo hubo (opcional)
    """
    update_data: Dict[str, Any] = {
        "account_status": account_status,
        "actualizada_en": datetime.utcnow().isoformat()
    }
    
    if ads_activos is not None:
        update_data["ads_activos"] = ads_activos
    
    if ultimo_error:
        update_data["ultimo_error"] = ultimo_error
        update_data["ultimo_error_at"] = datetime.utcnow().isoformat()
    
    result = (
        supabase.table("meta_ads_cuentas")
        .update(update_data)
        .eq("id", id_cuenta)
        .execute()
    )
    
    if result.data:
        logger.info(f"Estado actualizado para cuenta ID {id_cuenta}: status={account_status}")
    else:
        logger.warning(f"No se pudo actualizar estado de cuenta ID {id_cuenta}")


def registrar_error_cuenta(
    supabase: Client,
    id_cuenta: int,
    error_mensaje: str,
    error_code: Optional[str] = None
) -> None:
    """
    Registra un error en una cuenta publicitaria.
    
    Args:
        supabase: Cliente de Supabase
        id_cuenta: ID interno de la cuenta
        error_mensaje: Mensaje descriptivo del error
        error_code: Código de error opcional
    """
    error_data = {
        "mensaje": error_mensaje,
        "code": error_code,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    update_data = {
        "ultimo_error": error_data,
        "ultimo_error_at": datetime.utcnow().isoformat(),
        "actualizada_en": datetime.utcnow().isoformat()
    }
    
    result = (
        supabase.table("meta_ads_cuentas")
        .update(update_data)
        .eq("id", id_cuenta)
        .execute()
    )
    
    if result.data:
        logger.warning(f"Error registrado en cuenta ID {id_cuenta}: {error_mensaje}")
    else:
        logger.error(f"No se pudo registrar error en cuenta ID {id_cuenta}")
