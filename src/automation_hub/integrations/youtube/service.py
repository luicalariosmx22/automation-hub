"""
Servicio completo de YouTube para gestionar OAuth y uploads
"""
import logging
from typing import Optional, Dict
from automation_hub.integrations.youtube.oauth import YouTubeOAuthManager
from automation_hub.integrations.youtube.upload import YouTubeUploadService
from automation_hub.db.repositories.youtube_tokens_repo import YouTubeTokensRepository

logger = logging.getLogger(__name__)

class YouTubeService:
    """Servicio principal de YouTube - OAuth + Uploads"""
    
    def __init__(
        self,
        supabase_client,
        client_secrets_file: str = None
    ):
        """
        Inicializa el servicio de YouTube
        
        Args:
            supabase_client: Cliente de Supabase
            client_secrets_file: Ruta a credenciales de YouTube
        """
        self.oauth_manager = YouTubeOAuthManager(client_secrets_file)
        self.tokens_repo = YouTubeTokensRepository(supabase_client)
        self.supabase = supabase_client
    
    def get_authorization_url(
        self,
        cliente_id: str,
        redirect_uri: str
    ) -> str:
        """
        Obtiene URL para que el cliente autorice su canal de YouTube
        
        Args:
            cliente_id: ID del cliente
            redirect_uri: URL de callback
            
        Returns:
            URL de autorización
        """
        state = cliente_id  # Usar cliente_id como state
        auth_url, _ = self.oauth_manager.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state
        )
        
        logger.info(f"URL de autorización generada para cliente: {cliente_id}")
        return auth_url
    
    def handle_oauth_callback(
        self,
        code: str,
        cliente_id: str,
        redirect_uri: str
    ) -> Dict:
        """
        Maneja callback de OAuth y guarda tokens
        
        Args:
            code: Código de autorización
            cliente_id: ID del cliente
            redirect_uri: URL de callback
            
        Returns:
            Tokens guardados
        """
        # Intercambiar código por tokens
        tokens = self.oauth_manager.exchange_code_for_tokens(
            code=code,
            redirect_uri=redirect_uri
        )
        
        # Guardar en BD
        saved = self.tokens_repo.save_tokens(
            cliente_id=cliente_id,
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            expiry=tokens['expiry'],
            scopes=tokens['scopes']
        )
        
        logger.info(f"Cliente {cliente_id} conectó YouTube exitosamente")
        return saved
    
    def disconnect_youtube(self, cliente_id: str) -> bool:
        """
        Desconecta YouTube de un cliente
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            True si se desconectó
        """
        return self.tokens_repo.delete_tokens(cliente_id)
    
    def is_connected(self, cliente_id: str) -> bool:
        """
        Verifica si un cliente tiene YouTube conectado
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            True si está conectado
        """
        return self.tokens_repo.is_connected(cliente_id)
    
    def get_youtube_service_for_client(self, cliente_id: str):
        """
        Obtiene servicio de YouTube autenticado para un cliente
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            Servicio de YouTube API o None si no está conectado
        """
        # Obtener tokens
        tokens_data = self.tokens_repo.get_tokens(cliente_id)
        
        if not tokens_data:
            logger.warning(f"Cliente {cliente_id} no tiene YouTube conectado")
            return None
        
        # Validar y refrescar si es necesario
        access_token, expiry = self.oauth_manager.validate_and_refresh_if_needed(
            access_token=tokens_data['access_token'],
            refresh_token=tokens_data['refresh_token'],
            expiry_str=tokens_data['token_expiry']
        )
        
        # Si cambió el token, actualizar en BD
        if access_token != tokens_data['access_token']:
            self.tokens_repo.update_access_token(
                cliente_id=cliente_id,
                access_token=access_token,
                expiry=expiry
            )
        
        # Crear servicio autenticado
        youtube = self.oauth_manager.get_youtube_service(access_token)
        return youtube
    
    def upload_video(
        self,
        cliente_id: str,
        video_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        privacy_status: str = "private",
        validate_shorts: bool = True,
        source_type: str = None,
        source_id: str = None
    ) -> Dict:
        """
        Sube un video a YouTube para un cliente
        
        Args:
            cliente_id: ID del cliente
            video_path: Ruta al video local
            title: Título del video
            description: Descripción
            tags: Lista de tags
            privacy_status: 'public', 'private', 'unlisted'
            validate_shorts: Si validar para Shorts
            source_type: Tipo de origen (ej: 'facebook_post')
            source_id: ID del origen
            
        Returns:
            Dict con resultado del upload
        """
        # Obtener servicio autenticado
        youtube = self.get_youtube_service_for_client(cliente_id)
        
        if not youtube:
            raise ValueError(f"Cliente {cliente_id} no tiene YouTube conectado")
        
        # Crear servicio de upload
        upload_service = YouTubeUploadService(youtube)
        
        # Subir video
        result = upload_service.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
            validate_shorts=validate_shorts
        )
        
        # Guardar registro en BD
        validation = result.get('validation_info', {})
        
        self.supabase.table('youtube_videos').insert({
            'cliente_id': cliente_id,
            'video_id': result['videoId'],
            'video_url': result['url'],
            'title': title,
            'description': description,
            'tags': tags,
            'privacy_status': privacy_status,
            'is_short': result.get('is_short'),
            'duration': validation.get('duration'),
            'width': validation.get('width'),
            'height': validation.get('height'),
            'aspect_ratio': validation.get('aspect_ratio'),
            'upload_status': 'uploaded',
            'local_video_path': video_path,
            'source_type': source_type,
            'source_id': source_id
        }).execute()
        
        logger.info(
            f"Video subido a YouTube para cliente {cliente_id}: {result['url']}"
        )
        
        return result
    
    def get_video_status(
        self,
        cliente_id: str,
        video_id: str
    ) -> Dict:
        """
        Obtiene estado de procesamiento de un video
        
        Args:
            cliente_id: ID del cliente
            video_id: ID del video en YouTube
            
        Returns:
            Estado del video
        """
        youtube = self.get_youtube_service_for_client(cliente_id)
        
        if not youtube:
            raise ValueError(f"Cliente {cliente_id} no tiene YouTube conectado")
        
        upload_service = YouTubeUploadService(youtube)
        return upload_service.get_video_processing_status(video_id)
