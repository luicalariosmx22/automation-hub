"""
Repositorio para gestionar configuración de notificaciones de Telegram.
"""
import logging
from typing import List, Dict, Any, Optional, cast
from supabase import Client

logger = logging.getLogger(__name__)


def fetch_destinatarios_telegram(
    supabase: Client,
    nombre_nora: Optional[str] = None,
    job_name: Optional[str] = None,
    prioridad: Optional[str] = None,
    tipo_alerta: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene destinatarios de Telegram según filtros.
    
    Args:
        supabase: Cliente de Supabase
        nombre_nora: Nombre del cliente (opcional)
        job_name: Nombre del job que genera la alerta (opcional)
        prioridad: Prioridad de la alerta (opcional)
        tipo_alerta: Tipo de alerta (opcional)
        
    Returns:
        Lista de configuraciones que coinciden con los filtros
    """
    query = supabase.table("notificaciones_telegram_config").select("*")
    
    # Filtrar por activos
    query = query.eq("activo", True)
    
    # Si hay nombre_nora, filtrar por él o incluir "Sistema" (que recibe todo)
    if nombre_nora:
        query = query.in_("nombre_nora", [nombre_nora, "Sistema"])
    
    result = query.execute()
    
    if not result.data:
        logger.debug("No se encontraron configuraciones de notificaciones activas")
        return []
    
    # Filtrar en memoria por jobs, prioridades y tipos
    destinatarios_validos = []
    configs = cast(List[Dict[str, Any]], result.data)
    
    for config in configs:
        # Verificar si el job está permitido
        jobs_permitidos = config.get("jobs_permitidos")
        if isinstance(jobs_permitidos, list) and job_name and job_name not in jobs_permitidos:
            continue
        
        # Verificar si la prioridad está permitida
        prioridades_permitidas = config.get("prioridades_permitidas")
        if isinstance(prioridades_permitidas, list) and prioridad and prioridad not in prioridades_permitidas:
            continue
        
        # Verificar si el tipo de alerta está permitido
        tipos_permitidos = config.get("tipos_alerta_permitidos")
        if isinstance(tipos_permitidos, list) and tipo_alerta and tipo_alerta not in tipos_permitidos:
            continue
        
        destinatarios_validos.append(config)
    
    logger.debug(f"Encontrados {len(destinatarios_validos)} destinatarios válidos para notificar")
    return destinatarios_validos


def agregar_destinatario_telegram(
    supabase: Client,
    nombre_nora: str,
    chat_id: str,
    nombre_contacto: Optional[str] = None,
    jobs_permitidos: Optional[List[str]] = None,
    prioridades_permitidas: Optional[List[str]] = None,
    tipos_alerta_permitidos: Optional[List[str]] = None,
    notas: Optional[str] = None
) -> int:
    """
    Agrega un nuevo destinatario de notificaciones.
    
    Args:
        supabase: Cliente de Supabase
        nombre_nora: Cliente al que pertenece
        chat_id: Chat ID de Telegram
        nombre_contacto: Nombre descriptivo
        jobs_permitidos: Lista de jobs permitidos (None = todos)
        prioridades_permitidas: Lista de prioridades (None = todas)
        tipos_alerta_permitidos: Lista de tipos de alerta (None = todos)
        notas: Notas internas
        
    Returns:
        ID del registro creado
    """
    data = {
        "nombre_nora": nombre_nora,
        "chat_id": chat_id,
        "nombre_contacto": nombre_contacto,
        "jobs_permitidos": jobs_permitidos,
        "prioridades_permitidas": prioridades_permitidas,
        "tipos_alerta_permitidos": tipos_alerta_permitidos,
        "notas": notas,
        "activo": True
    }
    
    result = supabase.table("notificaciones_telegram_config").insert(data).execute()
    
    if result.data and isinstance(result.data, list) and len(result.data) > 0:
        first_item = cast(Dict[str, Any], result.data[0])
        config_id = int(first_item["id"])
        logger.info(f"Destinatario Telegram agregado: {nombre_contacto} ({chat_id})")
        return config_id
    
    raise Exception("Error al agregar destinatario Telegram")


def actualizar_destinatario_telegram(
    supabase: Client,
    config_id: int,
    **campos
) -> bool:
    """
    Actualiza configuración de un destinatario.
    
    Args:
        supabase: Cliente de Supabase
        config_id: ID de la configuración
        **campos: Campos a actualizar
        
    Returns:
        True si se actualizó correctamente
    """
    result = supabase.table("notificaciones_telegram_config")\
        .update(campos)\
        .eq("id", config_id)\
        .execute()
    
    if result.data:
        logger.info(f"Destinatario Telegram {config_id} actualizado")
        return True
    
    return False


def desactivar_destinatario_telegram(
    supabase: Client,
    config_id: int
) -> bool:
    """
    Desactiva un destinatario (no lo elimina).
    
    Args:
        supabase: Cliente de Supabase
        config_id: ID de la configuración
        
    Returns:
        True si se desactivó correctamente
    """
    return actualizar_destinatario_telegram(supabase, config_id, activo=False)
