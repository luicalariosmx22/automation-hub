"""
Repositorio para tabla meta_ads_anuncios_webhooks.
"""
import logging
from typing import List, Dict, Any, cast
from datetime import datetime, timedelta
from supabase import Client

logger = logging.getLogger(__name__)


def fetch_anuncios_rechazados_recientes(
    supabase: Client,
    horas_atras: int = 24
) -> List[Dict[str, Any]]:
    """
    Obtiene anuncios con status rechazado actualizados recientemente.
    
    Args:
        supabase: Cliente de Supabase
        horas_atras: Ventana de tiempo para considerar "reciente"
        
    Returns:
        Lista de anuncios rechazados con info completa
    """
    # Calcular timestamp de corte
    fecha_limite = datetime.utcnow() - timedelta(hours=horas_atras)
    fecha_limite_str = fecha_limite.isoformat()
    
    try:
        # Estados que indican rechazo
        estados_rechazo = ['DISAPPROVED', 'REJECTED']
        
        # Query con filtros
        query = supabase.table("meta_ads_anuncios_webhooks").select(
            "id, name, status, nombre_nora, id_cuenta_publicitaria, "
            "campaign_id, adset_id, updated_time, creative_title, creative_body"
        )
        
        # Filtrar por estado rechazado
        query = query.in_("status", estados_rechazo)
        
        # Filtrar por fecha reciente (últimas X horas)
        query = query.gte("updated_time", fecha_limite_str)
        
        # Ordenar por fecha desc
        query = query.order("updated_time", desc=True)
        
        result = query.execute()
        
        logger.info(f"Anuncios rechazados encontrados: {len(result.data)}")
        return cast(List[Dict[str, Any]], result.data)
    
    except Exception as e:
        logger.error(f"Error obteniendo anuncios rechazados: {e}", exc_info=True)
        raise
