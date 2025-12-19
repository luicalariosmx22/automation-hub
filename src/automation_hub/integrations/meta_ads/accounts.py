"""
Integración con Meta Ads API para obtener información de cuentas publicitarias.
"""
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

META_ADS_API_BASE = "https://graph.facebook.com/v18.0"


def get_ad_account_info(
    account_id: str,
    access_token: str
) -> Optional[Dict[str, Any]]:
    """
    Obtiene información de una cuenta publicitaria desde Meta Ads API.
    
    Args:
        account_id: ID de la cuenta (con prefijo act_)
        access_token: Token de acceso de Meta
        
    Returns:
        Información de la cuenta o None si hay error
    """
    # Asegurar que el ID tenga el prefijo act_
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
    
    url = f"{META_ADS_API_BASE}/{account_id}"
    params = {
        "access_token": access_token,
        "fields": "id,name,account_status,currency,timezone_name,created_time,amount_spent,balance"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"Info obtenida para cuenta {account_id}: status={data.get('account_status')}")
        return data
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Cuenta {account_id} no encontrada en Meta Ads API")
        else:
            logger.error(f"HTTP error obteniendo info de {account_id}: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Error obteniendo info de cuenta {account_id}: {e}")
        return None


def get_active_ads_count(
    account_id: str,
    access_token: str
) -> int:
    """
    Obtiene la cantidad de anuncios activos de una cuenta.
    
    Args:
        account_id: ID de la cuenta (con prefijo act_)
        access_token: Token de acceso de Meta
        
    Returns:
        Cantidad de anuncios activos
    """
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
    
    url = f"{META_ADS_API_BASE}/{account_id}/ads"
    params = {
        "access_token": access_token,
        "fields": "id,status",
        "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
        "limit": 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        count = len(data.get("data", []))
        logger.debug(f"Anuncios activos en {account_id}: {count}")
        return count
    
    except Exception as e:
        logger.error(f"Error obteniendo anuncios de {account_id}: {e}")
        return 0
