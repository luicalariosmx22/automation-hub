"""
OAuth 2.0 para YouTube Data API v3
Maneja autenticación y refresh de tokens por cliente
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Configuración OAuth
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

class YouTubeOAuthManager:
    """Gestor de OAuth 2.0 para YouTube por cliente"""
    
    def __init__(self, client_secrets_file: str = None):
        """
        Inicializa el gestor de OAuth
        
        Args:
            client_secrets_file: Ruta al archivo client_secrets.json de YouTube
        """
        self.client_secrets_file = client_secrets_file or os.getenv(
            'YOUTUBE_CLIENT_SECRETS_FILE',
            'credentials/youtube_client_secrets.json'
        )
        
        if not os.path.exists(self.client_secrets_file):
            raise FileNotFoundError(
                f"No se encontró el archivo de credenciales: {self.client_secrets_file}"
            )
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> tuple[str, str]:
        """
        Genera URL de autorización OAuth
        
        Args:
            redirect_uri: URL de callback
            state: Estado opcional para validación
            
        Returns:
            Tupla (authorization_url, state)
        """
        flow = Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=YOUTUBE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',  # Para obtener refresh_token
            include_granted_scopes='true',
            prompt='consent'  # Forzar pantalla de consentimiento para refresh_token
        )
        
        logger.info(f"URL de autorización generada para YouTube")
        return authorization_url, state
    
    def exchange_code_for_tokens(
        self, 
        code: str, 
        redirect_uri: str
    ) -> Dict[str, any]:
        """
        Intercambia código de autorización por tokens
        
        Args:
            code: Código de autorización de OAuth
            redirect_uri: URL de callback (debe coincidir con la del flow)
            
        Returns:
            Dict con access_token, refresh_token, expiry
        """
        flow = Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=YOUTUBE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        tokens = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        logger.info("Tokens de YouTube obtenidos exitosamente")
        return tokens
    
    def get_canal_info(self, access_token: str) -> Dict:
        """
        Obtiene información del canal usando channels.list con mine=true
        
        Args:
            access_token: Token de acceso válido
            
        Returns:
            Dict con canal_id y canal_titulo
        """
        youtube = self.get_youtube_service(access_token)
        
        request = youtube.channels().list(
            part="snippet",
            mine=True
        )
        response = request.execute()
        
        if not response.get('items'):
            raise Exception("No se encontró un canal asociado a esta cuenta")
        
        canal = response['items'][0]
        canal_info = {
            'canal_id': canal['id'],
            'canal_titulo': canal['snippet']['title']
        }
        
        logger.info(f"Canal obtenido: {canal_info['canal_titulo']} ({canal_info['canal_id']})")
        return canal_info
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, any]:
        """
        Refresca access_token usando refresh_token
        
        Args:
            refresh_token: Refresh token guardado
            
        Returns:
            Dict con nuevo access_token y expiry
        """
        # Cargar client_id y client_secret del archivo
        import json
        with open(self.client_secrets_file, 'r') as f:
            client_config = json.load(f)
            client_id = client_config['installed']['client_id']
            client_secret = client_config['installed']['client_secret']
            token_uri = client_config['installed']['token_uri']
        
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=YOUTUBE_SCOPES
        )
        
        # Refrescar
        credentials.refresh(Request())
        
        tokens = {
            'access_token': credentials.token,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        logger.info("Access token de YouTube refrescado")
        return tokens
    
    def get_youtube_service(self, access_token: str):
        """
        Crea servicio de YouTube API autenticado
        
        Args:
            access_token: Token de acceso válido
            
        Returns:
            Recurso de YouTube API
        """
        credentials = Credentials(token=access_token)
        
        youtube = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            credentials=credentials
        )
        
        return youtube
    
    def validate_and_refresh_if_needed(
        self,
        access_token: str,
        refresh_token: str,
        expiry_str: str
    ) -> tuple[str, str]:
        """
        Valida token y refresca si está expirado
        
        Args:
            access_token: Token actual
            refresh_token: Refresh token
            expiry_str: Fecha de expiración ISO format
            
        Returns:
            Tupla (access_token, expiry_str) actualizados
        """
        try:
            expiry = datetime.fromisoformat(expiry_str)
            now = datetime.utcnow()
            
            # Si expira en menos de 5 minutos, refrescar
            if expiry <= now + timedelta(minutes=5):
                logger.info("Token de YouTube expirado o próximo a expirar, refrescando...")
                tokens = self.refresh_access_token(refresh_token)
                return tokens['access_token'], tokens['expiry']
            
            return access_token, expiry_str
            
        except Exception as e:
            logger.error(f"Error validando/refrescando token: {e}")
            raise
