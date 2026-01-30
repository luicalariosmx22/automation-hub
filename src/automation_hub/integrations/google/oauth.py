"""
Manejo de autenticación OAuth2 con Google.
"""
import logging
import os
from typing import Optional
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from automation_hub.db.supabase_client import create_client_from_env

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


def get_gbp_creds_from_db(tenant: str = "default") -> Credentials:
    """
    Obtiene credenciales de GBP desde la tabla google_oauth_tokens en Supabase.
    
    Args:
        tenant: Nombre del tenant (ej: 'aura', 'default')
    
    Returns:
        Credentials de Google con token válido
        
    Raises:
        ValueError: Si no se encuentra el token o falla la validación
        Exception: Si falla el refresh del token
    """
    supabase = create_client_from_env()
    
    # Leer client_id y client_secret del .env
    client_id = _clean(os.getenv("GOOGLE_CLIENT_ID"))
    client_secret = _clean(os.getenv("GOOGLE_CLIENT_SECRET"))
    
    # Validar credenciales de OAuth
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID no configurado o vacío")
    if not client_secret:
        raise ValueError("GOOGLE_CLIENT_SECRET no configurado o vacío")
    if not client_id.endswith(".apps.googleusercontent.com"):
        raise ValueError("GOOGLE_CLIENT_ID debe terminar en .apps.googleusercontent.com")
    if len(client_secret) < 20:
        raise ValueError("GOOGLE_CLIENT_SECRET parece inválido (longitud insuficiente)")
    
    # Obtener token desde la base de datos
    try:
        result = supabase.table("google_oauth_tokens").select("*").eq(
            "tenant", tenant
        ).eq("provider", "google").execute()
        
        if not result.data:
            raise ValueError(f"No se encontró token de Google OAuth para el tenant '{tenant}' en la base de datos")
        
        token_data = result.data[0]
        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at")
        
        if not refresh_token:
            raise ValueError(f"refresh_token no encontrado para el tenant '{tenant}'")
        
        # Crear credenciales
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Verificar si necesita refresh
        needs_refresh = True
        if access_token and expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_dt > datetime.now(timezone.utc):
                    needs_refresh = False
                    logger.info(f"Token aún válido para tenant '{tenant}'")
            except Exception:
                pass
        
        # Refrescar si es necesario
        if needs_refresh:
            logger.info(f"Refrescando token de acceso para tenant '{tenant}'")
            request = Request()
            credentials.refresh(request)
            
            # Actualizar token en la base de datos
            update_data = {
                "access_token": credentials.token,
                "expires_at": datetime.fromtimestamp(credentials.expiry.timestamp(), tz=timezone.utc).isoformat() if credentials.expiry else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("google_oauth_tokens").update(update_data).eq(
                "tenant", tenant
            ).eq("provider", "google").execute()
            
            logger.info(f"Token actualizado exitosamente para tenant '{tenant}'")
        
        return credentials
    
    except Exception as e:
        logger.error(f"Error obteniendo token de Google OAuth para tenant '{tenant}': {e}")
        raise


def get_gbp_creds_from_env() -> Credentials:
    """
    Obtiene credenciales de GBP desde la base de datos (mantiene compatibilidad).
    Por defecto usa el tenant 'aura'.
    
    Returns:
        Credentials de Google con token válido
        
    Raises:
        ValueError: Si faltan variables o son inválidas
        Exception: Si falla el refresh del token
    """
    # Intentar obtener el tenant desde variable de entorno, sino usar 'aura'
    tenant = os.getenv("GOOGLE_OAUTH_TENANT", "aura")
    return get_gbp_creds_from_db(tenant)


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
