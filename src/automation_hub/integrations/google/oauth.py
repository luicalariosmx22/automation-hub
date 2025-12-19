"""
Manejo de autenticación OAuth2 con Google.
"""
import logging
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


def get_bearer_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """
    Obtiene un token de acceso válido usando refresh token de Google OAuth2.
    
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
