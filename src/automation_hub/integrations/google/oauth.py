"""
Manejo de autenticación OAuth2 con Google.
"""
import logging
import os
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


def _clean(value: Optional[str]) -> Optional[str]:
    """
    Limpia un valor de variable de entorno removiendo espacios y comillas.
    
    Args:
        value: Valor a limpiar
        
    Returns:
        Valor limpio o None
    """
    if value is None:
        return None
    
    # Eliminar espacios al inicio/final
    v = value.strip()
    
    # Remover comillas si están al inicio y final
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ["'", '"']:
        v = v[1:-1].strip()
    
    return v if v else None


def get_gbp_creds_from_env() -> Credentials:
    """
    Obtiene credenciales de GBP desde variables de entorno y las refresca.
    Implementa validaciones similares a Nora panel_cliente_google_maps.
    
    Returns:
        Credentials de Google con token válido
        
    Raises:
        ValueError: Si faltan variables o son inválidas
        Exception: Si falla el refresh del token
    """
    # Leer y limpiar variables de entorno
    client_id = _clean(os.getenv("GOOGLE_CLIENT_ID"))
    client_secret = _clean(os.getenv("GOOGLE_CLIENT_SECRET"))
    refresh_token = _clean(os.getenv("GBP_REFRESH_TOKEN"))
    
    # Validar que existan
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID no configurado o vacío")
    if not client_secret:
        raise ValueError("GOOGLE_CLIENT_SECRET no configurado o vacío")
    if not refresh_token:
        raise ValueError("GBP_REFRESH_TOKEN no configurado o vacío")
    
    # Validar formato client_id
    if not client_id.endswith(".apps.googleusercontent.com"):
        raise ValueError("GOOGLE_CLIENT_ID debe terminar en .apps.googleusercontent.com")
    
    # Validar longitud mínima del secret
    if len(client_secret) < 20:
        raise ValueError("GOOGLE_CLIENT_SECRET parece inválido (longitud insuficiente)")
    
    # Crear credenciales
    try:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Refrescar token
        logger.info("Refrescando token de acceso de Google OAuth")
        request = Request()
        credentials.refresh(request)
        
        logger.info("Token de acceso obtenido exitosamente")
        return credentials
    
    except Exception as e:
        logger.error(f"Error obteniendo token de acceso de Google: {e}")
        raise ValueError("No se pudo refrescar el token de OAuth. Verifica que el refresh_token sea válido y corresponda al client_id/secret configurado") from e


def get_bearer_header() -> dict:
    """
    Obtiene header de autorización Bearer listo para usar en requests.
    
    Returns:
        Dict con header Authorization
    """
    creds = get_gbp_creds_from_env()
    return {"Authorization": f"Bearer {creds.token}"}


def get_bearer_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """
    Obtiene un token de acceso válido usando refresh token de Google OAuth2.
    
    DEPRECATED: Usar get_gbp_creds_from_env() o get_bearer_header() en su lugar.
    
    Args:
        client_id: Client ID de Google Cloud
        client_secret: Client Secret de Google Cloud
        refresh_token: Refresh token del usuario
        
    Returns:
        Access token válido (solo el token, sin "Bearer ")
        
    Raises:
        ValueError: Si algún parámetro está vacío después de limpieza
        Exception: Si falla el refresh del token
    """
    # Limpiar inputs
    clean_client_id = _clean(client_id)
    clean_client_secret = _clean(client_secret)
    clean_refresh_token = _clean(refresh_token)
    
    # Validar que no estén vacíos
    if not clean_client_id or not clean_client_secret or not clean_refresh_token:
        missing = []
        if not clean_client_id:
            missing.append("GOOGLE_CLIENT_ID")
        if not clean_client_secret:
            missing.append("GOOGLE_CLIENT_SECRET")
        if not clean_refresh_token:
            missing.append("GBP_REFRESH_TOKEN")
        raise ValueError(f"Variables de OAuth vacías o inválidas: {', '.join(missing)}")
    
    try:
        credentials = Credentials(
            token=None,
            refresh_token=clean_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=clean_client_id,
            client_secret=clean_client_secret
        )
        
        # Forzar refresh del token
        request = Request()
        credentials.refresh(request)
        
        logger.debug("Token de acceso obtenido exitosamente")
        return str(credentials.token)
    
    except Exception as e:
        logger.error(f"Error obteniendo token de acceso: {e}")
        raise
