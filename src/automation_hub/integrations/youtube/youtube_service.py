"""
Servicio completo de YouTube - OAuth + Uploads con canal_id
"""
import logging
from typing import Optional, Dict, List
from automation_hub.integrations.youtube.oauth import YouTubeOAuthManager
from automation_hub.integrations.youtube.upload import YouTubeUploadService
from automation_hub.db.repositories.youtube_conexiones_repo import YouTubeConexionesRepository

logger = logging.getLogger(__name__)

class YouTubeService:
    """
    Servicio principal de YouTube
    
    IMPORTANTE: Solo el OWNER del canal puede usar YouTube APIs.
    Usuarios con permisos de manager/editor NO pueden administrar por API.
    """
    
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
        self.conexiones_repo = YouTubeConexionesRepository(supabase_client)
        self.supabase = supabase_client
    
    def get_authorization_url(
        self,
        cliente_id: str,
        redirect_uri: str
    ) -> str:
        """
        Obtiene URL para que el cliente autorice su canal de YouTube
        
        IMPORTANTE: El usuario DEBE ser OWNER del canal, no manager/editor.
        
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
        Maneja callback de OAuth y guarda tokens con información del canal
        
        Args:
            code: Código de autorización
            cliente_id: ID del cliente
            redirect_uri: URL de callback
            
        Returns:
            Conexión guardada con canal_id y canal_titulo
        """
        # Intercambiar código por tokens
        tokens = self.oauth_manager.exchange_code_for_tokens(
            code=code,
            redirect_uri=redirect_uri
        )
        
        # Obtener información del canal usando channels.list(mine=true)
        canal_info = self.oauth_manager.get_canal_info(tokens['access_token'])
        
        # Parsear expiry
        from datetime import datetime
        token_expira_en = None
        if tokens.get('expiry'):
            token_expira_en = datetime.fromisoformat(tokens['expiry'].replace('Z', '+00:00'))
        
        # Guardar conexión con canal_id y canal_titulo
        saved = self.conexiones_repo.save_conexion(
            cliente_id=cliente_id,
            canal_id=canal_info['canal_id'],
            canal_titulo=canal_info['canal_titulo'],
            refresh_token=tokens['refresh_token'],
            access_token=tokens['access_token'],
            token_expira_en=token_expira_en
        )
        
        logger.info(
            f"Cliente {cliente_id} conectó canal YouTube: "
            f"{canal_info['canal_titulo']} ({canal_info['canal_id']})"
        )
        
        return saved
    
    def disconnect_youtube(self, conexion_id: str) -> bool:
        """
        Desconecta un canal de YouTube
        
        Args:
            conexion_id: ID de la conexión
            
        Returns:
            True si se desconectó
        """
        return self.conexiones_repo.delete_conexion(conexion_id)
    
    def is_connected(self, cliente_id: str) -> bool:
        """
        Verifica si un cliente tiene YouTube conectado
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            True si está conectado
        """
        return self.conexiones_repo.is_connected(cliente_id)
    
    def get_canales_conectados(self, cliente_id: str) -> List[Dict]:
        """
        Obtiene lista de canales conectados para un cliente
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            Lista de canales con canal_id, canal_titulo, created_at
        """
        conexiones = self.conexiones_repo.get_conexiones_cliente(cliente_id)
        
        return [
            {
                'id': c['id'],
                'canal_id': c['canal_id'],
                'canal_titulo': c['canal_titulo'],
                'created_at': c['created_at']
            }
            for c in conexiones
        ]
    
    def get_youtube_service_for_cliente(
        self,
        cliente_id: str,
        canal_id: Optional[str] = None
    ):
        """
        Obtiene servicio de YouTube autenticado para un cliente
        
        Args:
            cliente_id: ID del cliente
            canal_id: ID del canal (opcional, usa el primero si no se especifica)
            
        Returns:
            Servicio de YouTube API o None si no está conectado
        """
        # Obtener conexión
        conexion = self.conexiones_repo.get_conexion(cliente_id, canal_id)
        
        if not conexion:
            logger.warning(f"Cliente {cliente_id} no tiene YouTube conectado")
            return None, None
        
        # Validar y refrescar si es necesario
        from datetime import datetime
        expiry_str = conexion.get('token_expira_en')
        
        access_token, expiry = self.oauth_manager.validate_and_refresh_if_needed(
            access_token=conexion['access_token'],
            refresh_token=conexion['refresh_token'],
            expiry_str=expiry_str
        )
        
        # Si cambió el token, actualizar en BD
        if access_token != conexion['access_token']:
            self.conexiones_repo.update_access_token(
                conexion_id=conexion['id'],
                access_token=access_token,
                token_expira_en=expiry
            )
        
        # Crear servicio autenticado
        youtube = self.oauth_manager.get_youtube_service(access_token)
        return youtube, conexion['id']
    
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
        source_id: str = None,
        canal_id: Optional[str] = None
    ) -> Dict:
        """
        Sube un video a YouTube usando videos.insert
        
        NOTA: "Shorts" no es un endpoint separado, se detecta automáticamente
        por duración (<=60s) y orientación vertical.
        
        Args:
            cliente_id: ID del cliente
            video_path: Ruta al video local
            title: Título del video
            description: Descripción
            tags: Lista de tags
            privacy_status: 'public', 'private', 'unlisted'
            validate_shorts: Si validar para Shorts (<=180s, vertical/cuadrado)
            source_type: Tipo de origen (ej: 'facebook_post')
            source_id: ID del origen
            canal_id: ID del canal (opcional)
            
        Returns:
            Dict con resultado del upload
        """
        # Obtener servicio autenticado
        youtube, conexion_id = self.get_youtube_service_for_cliente(cliente_id, canal_id)
        
        if not youtube:
            raise ValueError(
                f"Cliente {cliente_id} no tiene YouTube conectado. "
                "IMPORTANTE: Solo el OWNER del canal puede conectar por API."
            )
        
        # Crear servicio de upload
        upload_service = YouTubeUploadService(youtube)
        
        # Subir video con MediaFileUpload resumable
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
            'conexion_id': conexion_id,
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
        video_id: str,
        canal_id: Optional[str] = None
    ) -> Dict:
        """
        Obtiene estado de procesamiento de un video
        
        Args:
            cliente_id: ID del cliente
            video_id: ID del video en YouTube
            canal_id: ID del canal (opcional)
            
        Returns:
            Estado del video
        """
        youtube, _ = self.get_youtube_service_for_cliente(cliente_id, canal_id)
        
        if not youtube:
            raise ValueError(f"Cliente {cliente_id} no tiene YouTube conectado")
        
        upload_service = YouTubeUploadService(youtube)
        return upload_service.get_video_processing_status(video_id)
