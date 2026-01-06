"""
Repositorio para gestionar tokens de YouTube OAuth por cliente
"""
import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class YouTubeConexionesRepository:
    """Gestiona conexiones de YouTube por cliente"""
    
    def __init__(self, supabase_client):
        """
        Inicializa el repository
        
        Args:
            supabase_client: Cliente de Supabase
        """
        self.supabase = supabase_client
        self.table_name = 'youtube_conexiones'
    
    def save_tokens(
        self,
        cliente_id: str,
        access_token: str,
        refresh_token: str,
        expiry: str,
        scopes: list,
        user_email: Optional[str] = None
    ) -> Dict:
        """
        Guarda o actualiza tokens de YouTube para un cliente
        
        Args:
            cliente_id: ID del cliente/empresa
            access_token: Token de acceso
            refresh_token: Refresh token (persistente)
            expiry: Fecha de expiración ISO format
            scopes: Lista de scopes autorizados
            user_email: Email del usuario de YouTube (opcional)
            
        Returns:
            Registro guardado
        """
        try:
            data = {
                'cliente_id': cliente_id,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expiry': expiry,
                'scopes': scopes,
                'user_email': user_email,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Intentar actualizar, si no existe insertar
            response = self.supabase.table(self.table_name)\
                .upsert(data, on_conflict='cliente_id')\
                .execute()
            
            logger.info(f"Tokens de YouTube guardados para cliente: {cliente_id}")
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error guardando tokens de YouTube: {e}")
            raise
    
    def get_tokens(self, cliente_id: str) -> Optional[Dict]:
        """
        Obtiene tokens de YouTube de un cliente
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            Dict con tokens o None si no existe
        """
        try:
            response = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("cliente_id", cliente_id)\
                .execute()
            
            if response.data:
                logger.info(f"Tokens de YouTube encontrados para cliente: {cliente_id}")
                return response.data[0]
            
            logger.info(f"No se encontraron tokens de YouTube para cliente: {cliente_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo tokens de YouTube: {e}")
            raise
    
    def update_access_token(
        self,
        cliente_id: str,
        access_token: str,
        expiry: str
    ) -> Dict:
        """
        Actualiza solo el access_token (después de refresh)
        
        Args:
            cliente_id: ID del cliente
            access_token: Nuevo token de acceso
            expiry: Nueva fecha de expiración
            
        Returns:
            Registro actualizado
        """
        try:
            data = {
                'access_token': access_token,
                'token_expiry': expiry,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table(self.table_name)\
                .update(data)\
                .eq("cliente_id", cliente_id)\
                .execute()
            
            logger.info(f"Access token de YouTube actualizado para cliente: {cliente_id}")
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error actualizando access token: {e}")
            raise
    
    def delete_tokens(self, cliente_id: str) -> bool:
        """
        Elimina tokens de YouTube de un cliente (desconectar)
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            True si se eliminó
        """
        try:
            response = self.supabase.table(self.table_name)\
                .delete()\
                .eq("cliente_id", cliente_id)\
                .execute()
            
            logger.info(f"Tokens de YouTube eliminados para cliente: {cliente_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando tokens: {e}")
            raise
    
    def is_connected(self, cliente_id: str) -> bool:
        """
        Verifica si un cliente tiene YouTube conectado
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            True si tiene tokens guardados
        """
        tokens = self.get_tokens(cliente_id)
        return tokens is not None and tokens.get('refresh_token') is not None
