"""
Servicio de subida de videos a YouTube (Shorts)
"""
import os
import logging
import subprocess
import json
from typing import Optional, Dict
from pathlib import Path
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class YouTubeUploadService:
    """Servicio para subir videos a YouTube"""
    
    def __init__(self, youtube_service):
        """
        Inicializa el servicio de upload
        
        Args:
            youtube_service: Recurso de YouTube API autenticado
        """
        self.youtube = youtube_service
    
    def validate_video_for_shorts(self, video_path: str) -> Dict[str, any]:
        """
        Valida si un video cumple requisitos de YouTube Shorts
        
        Requisitos Shorts:
        - Duración <= 180 segundos (3 minutos)
        - Aspect ratio vertical (9:16) o cuadrado (1:1)
        
        Args:
            video_path: Ruta al archivo de video
            
        Returns:
            Dict con is_shorts_compatible, duration, width, height, aspect_ratio
        """
        try:
            # Usar ffprobe para obtener metadata del video
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            metadata = json.loads(result.stdout)
            
            # Extraer información
            duration = float(metadata['format']['duration'])
            
            # Buscar stream de video
            video_stream = None
            for stream in metadata['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ValueError("No se encontró stream de video")
            
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            aspect_ratio = width / height if height > 0 else 0
            
            # Validar requisitos de Shorts
            is_duration_valid = duration <= 180  # 3 minutos
            
            # Vertical: aspect ratio cercano a 9:16 (0.5625)
            # Cuadrado: aspect ratio cercano a 1:1 (1.0)
            is_vertical = 0.5 <= aspect_ratio <= 0.6  # ~9:16
            is_square = 0.9 <= aspect_ratio <= 1.1    # ~1:1
            is_aspect_valid = is_vertical or is_square
            
            is_shorts_compatible = is_duration_valid and is_aspect_valid
            
            result = {
                'is_shorts_compatible': is_shorts_compatible,
                'duration': duration,
                'width': width,
                'height': height,
                'aspect_ratio': aspect_ratio,
                'is_vertical': is_vertical,
                'is_square': is_square,
                'is_duration_valid': is_duration_valid,
                'is_aspect_valid': is_aspect_valid
            }
            
            logger.info(
                f"Video validado: {duration:.1f}s, {width}x{height}, "
                f"aspect {aspect_ratio:.2f}, Shorts: {is_shorts_compatible}"
            )
            
            return result
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ejecutando ffprobe: {e}")
            raise
        except Exception as e:
            logger.error(f"Error validando video: {e}")
            raise
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        category_id: str = "22",  # 22 = People & Blogs
        privacy_status: str = "private",
        made_for_kids: bool = False,
        validate_shorts: bool = True
    ) -> Dict[str, any]:
        """
        Sube video a YouTube usando resumable upload
        
        Args:
            video_path: Ruta al archivo de video
            title: Título del video
            description: Descripción del video
            tags: Lista de tags
            category_id: ID de categoría de YouTube
            privacy_status: 'public', 'private', 'unlisted'
            made_for_kids: Si el video es para niños
            validate_shorts: Si validar requisitos de Shorts
            
        Returns:
            Dict con videoId, url, is_short, validation_info
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"No se encontró el video: {video_path}")
        
        # Validar para Shorts si se solicita
        validation_info = None
        if validate_shorts:
            try:
                validation_info = self.validate_video_for_shorts(video_path)
                
                if not validation_info['is_shorts_compatible']:
                    logger.warning(
                        f"Video NO cumple requisitos de Shorts: "
                        f"duration={validation_info['duration']:.1f}s, "
                        f"aspect={validation_info['aspect_ratio']:.2f}"
                    )
            except Exception as e:
                logger.warning(f"No se pudo validar video para Shorts: {e}")
        
        # Preparar body del request
        body = {
            'snippet': {
                'title': title[:100],  # Max 100 caracteres
                'description': description[:5000],  # Max 5000 caracteres
                'tags': tags[:500] if tags else [],  # Max 500 tags
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': made_for_kids
            }
        }
        
        # Preparar media upload (resumable)
        media = MediaFileUpload(
            video_path,
            chunksize=10 * 1024 * 1024,  # 10MB chunks
            resumable=True
        )
        
        try:
            logger.info(f"Iniciando subida de video a YouTube: {title}")
            
            # Ejecutar upload
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")
            
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            result = {
                'videoId': video_id,
                'url': video_url,
                'title': title,
                'privacy_status': privacy_status,
                'is_short': validation_info['is_shorts_compatible'] if validation_info else None,
                'validation_info': validation_info
            }
            
            logger.info(f"✅ Video subido exitosamente: {video_url}")
            
            return result
            
        except HttpError as e:
            logger.error(f"Error HTTP subiendo video: {e}")
            raise
        except Exception as e:
            logger.error(f"Error subiendo video: {e}")
            raise
    
    def get_video_processing_status(self, video_id: str) -> Dict[str, any]:
        """
        Obtiene estado de procesamiento del video
        
        Args:
            video_id: ID del video en YouTube
            
        Returns:
            Dict con processing_status, upload_status, failure_reason
        """
        try:
            request = self.youtube.videos().list(
                part='processingDetails,status',
                id=video_id
            )
            
            response = request.execute()
            
            if not response.get('items'):
                return {'error': 'Video no encontrado'}
            
            video = response['items'][0]
            processing = video.get('processingDetails', {})
            status = video.get('status', {})
            
            return {
                'processing_status': processing.get('processingStatus'),
                'processing_progress': processing.get('processingProgress', {}),
                'upload_status': status.get('uploadStatus'),
                'failure_reason': status.get('failureReason'),
                'rejection_reason': status.get('rejectionReason'),
                'privacy_status': status.get('privacyStatus'),
                'publishAt': status.get('publishAt')
            }
            
        except HttpError as e:
            logger.error(f"Error obteniendo estado de video: {e}")
            raise
