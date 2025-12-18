"""
Cliente de Supabase para automation-hub.
"""
import logging
from supabase import create_client as supabase_create_client, Client

logger = logging.getLogger(__name__)


def create_client(supabase_url: str, supabase_key: str) -> Client:
    """
    Crea y retorna un cliente de Supabase.
    
    Args:
        supabase_url: URL del proyecto Supabase
        supabase_key: API key de Supabase
        
    Returns:
        Cliente de Supabase configurado
    """
    try:
        client = supabase_create_client(supabase_url, supabase_key)
        logger.debug("Cliente Supabase creado exitosamente")
        return client
    except Exception as e:
        logger.error(f"Error creando cliente Supabase: {e}")
        raise
