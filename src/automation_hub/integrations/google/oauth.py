"""
Manejo de autenticación OAuth2 con Google.
"""
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


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
        Exception: Si falla el refresh del token
    """
    try:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Forzar refresh del token
        request = Request()
        credentials.refresh(request)
        
        logger.debug("Token de acceso obtenido exitosamente")
        return credentials.token
    
    except Exception as e:
        logger.error(f"Error obteniendo token de acceso: {e}")
        raise
