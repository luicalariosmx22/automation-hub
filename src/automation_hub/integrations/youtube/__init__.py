"""
Integración con YouTube para subir videos a Shorts

IMPORTANTE: Solo el OWNER del canal puede conectar YouTube.
Los permisos de Manager/Editor en YouTube Studio NO funcionan con APIs.
"""

from .youtube_service import YouTubeService
from .oauth import YouTubeOAuthManager
from .upload import YouTubeUploadService

__all__ = [
    'YouTubeService',
    'YouTubeOAuthManager',
    'YouTubeUploadService'
]
