"""
Cliente de Supabase para automation-hub.
"""
import logging
import os
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)


def _clean_env(value: Optional[str]) -> Optional[str]:
    """
    Limpia un valor de variable de entorno removiendo espacios y comillas.
    
    Args:
        value: Valor a limpiar
        
    Returns:
        Valor limpio o None
    """
    if value is None:
        return None
    
    v = value.strip()
    
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ['"', "'"]:
        v = v[1:-1].strip()
    
    return v


def create_client_from_env() -> Client:
    """
    Crea y retorna un cliente de Supabase desde variables de entorno.
    Lee SUPABASE_URL y SUPABASE_KEY con limpieza automática.
    
    Returns:
        Cliente de Supabase configurado
        
    Raises:
        ValueError: Si faltan variables o son inválidas
    """
    url = _clean_env(os.getenv("SUPABASE_URL"))
    key = _clean_env(os.getenv("SUPABASE_KEY"))
    
    if not url or not key:
        missing = []
        if not url:
            missing.append("SUPABASE_URL")
        if not key:
            missing.append("SUPABASE_KEY")
        raise ValueError(f"Variables de Supabase faltantes o vacías: {', '.join(missing)}")
    
    logger.info(f"Supabase url loaded: {url}")
    logger.info(f"Supabase key length: {len(key)}")
    
    return create_client(url, key)
