"""
Repository para gestionar conexiones de YouTube en Supabase
"""
import logging
from typing import Optional, Dict, List
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
    
    def save_conexion(
        self,
        cliente_id: str,
        canal_id: str,
        canal_titulo: str,
        refresh_token: str,
        access_token: Optional[str] = None,
        token_expira_en: Optional[datetime] = None
    ) -> Dict:
        """
        Guarda conexión de YouTube para un cliente
        
        Args:
            cliente_id: ID del cliente
            canal_id: ID del canal de YouTube
            canal_titulo: Título del canal
            refresh_token: Token de refresh
            access_token: Token de acceso (opcional)
            token_expira_en: Fecha de expiración del access_token
            
        Returns:
            Registro guardado
        """
        data = {
            'cliente_id': cliente_id,
            'canal_id': canal_id,
            'canal_titulo': canal_titulo,
            'refresh_token': refresh_token,
            'access_token': access_token,
            'token_expira_en': token_expira_en.isoformat() if token_expira_en else None
        }
        
        # Upsert: insertar o actualizar si ya existe
        result = self.supabase.table(self.table_name).upsert(
            data,
            on_conflict='cliente_id,canal_id'
        ).execute()
        
        if result.data:
            logger.info(f"Conexión guardada - cliente: {cliente_id}, canal: {canal_titulo}")
            return result.data[0]
        else:
            logger.error(f"Error guardando conexión para cliente: {cliente_id}")
            raise Exception("Error al guardar conexión de YouTube")
    
    def get_conexion(self, cliente_id: str, canal_id: Optional[str] = None) -> Optional[Dict]:
        """
        Obtiene conexión de YouTube de un cliente
        
        Args:
            cliente_id: ID del cliente
            canal_id: ID del canal (opcional, toma el primero si no se especifica)
            
        Returns:
            Conexión o None si no existe
        """
        query = self.supabase.table(self.table_name).select('*').eq('cliente_id', cliente_id)
        
        if canal_id:
            query = query.eq('canal_id', canal_id)
        
        result = query.execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return None
    
    def get_conexiones_cliente(self, cliente_id: str) -> List[Dict]:
        """
        Obtiene todas las conexiones de YouTube de un cliente
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            Lista de conexiones
        """
        result = self.supabase.table(self.table_name).select('*').eq(
            'cliente_id',
            cliente_id
        ).execute()
        
        return result.data if result.data else []
    
    def update_access_token(
        self,
        conexion_id: str,
        access_token: str,
        token_expira_en: datetime
    ) -> Dict:
        """
        Actualiza solo el access_token (cuando se refresca)
        
        Args:
            conexion_id: ID de la conexión
            access_token: Nuevo token de acceso
            token_expira_en: Nueva fecha de expiración
            
        Returns:
            Registro actualizado
        """
        data = {
            'access_token': access_token,
            'token_expira_en': token_expira_en.isoformat()
        }
        
        result = self.supabase.table(self.table_name).update(data).eq(
            'id',
            conexion_id
        ).execute()
        
        if result.data:
            logger.info(f"Access token actualizado para conexión: {conexion_id}")
            return result.data[0]
        else:
            raise Exception("Error al actualizar access token")
    
    def delete_conexion(self, conexion_id: str) -> bool:
        """
        Elimina una conexión de YouTube
        
        Args:
            conexion_id: ID de la conexión
            
        Returns:
            True si se eliminó
        """
        result = self.supabase.table(self.table_name).delete().eq(
            'id',
            conexion_id
        ).execute()
        
        logger.info(f"Conexión eliminada: {conexion_id}")
        return True
    
    def is_connected(self, cliente_id: str) -> bool:
        """
        Verifica si un cliente tiene YouTube conectado
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            True si tiene al menos una conexión activa
        """
        conexiones = self.get_conexiones_cliente(cliente_id)
        return len(conexiones) > 0
