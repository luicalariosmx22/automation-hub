"""
Cliente de Telegram para enviar notificaciones de alertas.
"""
import logging
import os
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Cliente para enviar notificaciones vía Telegram Bot."""
    
    def __init__(self, bot_token: Optional[str] = None, default_chat_id: Optional[str] = None, bot_nombre: Optional[str] = None):
        """
        Inicializa el notificador de Telegram.
        
        Args:
            bot_token: Token del bot de Telegram (opcional, usa env var si no se provee)
            default_chat_id: Chat ID por defecto (opcional, usa env var si no se provee)
            bot_nombre: Nombre del bot en la BD (ej: "Bot Meta Ads")
        """
        # Si se especifica nombre de bot, buscar en BD
        if bot_nombre and not bot_token:
            try:
                from automation_hub.db.supabase_client import create_client_from_env
                supabase = create_client_from_env()
                result = supabase.table("telegram_bots").select("token").eq("nombre", bot_nombre).eq("activo", True).single().execute()
                if result.data:
                    bot_token = result.data.get("token")
                    logger.info(f"Bot '{bot_nombre}' cargado desde BD")
                else:
                    logger.warning(f"Bot '{bot_nombre}' no encontrado en BD, usando env var")
            except Exception as e:
                logger.warning(f"Error cargando bot desde BD: {e}, usando env var")
        
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.default_chat_id = default_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def enviar_mensaje(
        self,
        mensaje: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Envía un mensaje a un chat de Telegram.
        
        Args:
            mensaje: Texto del mensaje a enviar
            chat_id: ID del chat (usa default si no se provee)
            parse_mode: Modo de parseo (HTML, Markdown, MarkdownV2)
            disable_notification: Si True, envía sin notificación sonora
            
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN no configurado")
            return False
        
        target_chat_id = chat_id or self.default_chat_id
        if not target_chat_id:
            logger.error("No se especificó chat_id y no hay default")
            return False
        
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": mensaje,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.info(f"Mensaje enviado a Telegram chat {target_chat_id}")
                return True
            else:
                logger.error(f"Error en respuesta de Telegram: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando mensaje a Telegram: {e}")
            return False
    
    def enviar_alerta(
        self,
        nombre: str,
        descripcion: str,
        prioridad: str = "baja",
        datos: Optional[Dict[str, Any]] = None,
        chat_id: Optional[str] = None
    ) -> bool:
        """
        Envía una alerta formateada a Telegram.
        
        Args:
            nombre: Título de la alerta
            descripcion: Descripción detallada
            prioridad: Nivel de prioridad (alta, media, baja)
            datos: Datos adicionales para incluir
            chat_id: ID del chat (usa default si no se provee)
            
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        # Emojis según prioridad
        emoji_map = {
            "alta": "🚨",
            "media": "⚠️",
            "baja": "ℹ️"
        }
        emoji = emoji_map.get(prioridad.lower(), "📢")
        
        # Construir mensaje
        mensaje_partes = [
            f"{emoji} <b>{nombre}</b>",
            "",
            descripcion
        ]
        
        # Agregar datos adicionales si existen
        if datos:
            mensaje_partes.append("")
            mensaje_partes.append("📊 <b>Detalles:</b>")
            for key, value in datos.items():
                # Formatear keys legibles
                key_legible = key.replace("_", " ").title()
                mensaje_partes.append(f"  • {key_legible}: {value}")
        
        mensaje = "\n".join(mensaje_partes)
        
        # Alertas de alta prioridad con notificación sonora
        disable_notification = (prioridad.lower() != "alta")
        
        return self.enviar_mensaje(
            mensaje=mensaje,
            chat_id=chat_id,
            disable_notification=disable_notification
        )


def notificar_alerta_telegram(
    nombre: str,
    descripcion: str,
    prioridad: str = "baja",
    datos: Optional[Dict[str, Any]] = None,
    chat_id: Optional[str] = None,
    nombre_nora: Optional[str] = None,
    job_name: Optional[str] = None,
    tipo_alerta: Optional[str] = None
) -> bool:
    """
    Función helper para enviar una alerta a Telegram.
    Consulta la configuración para determinar destinatarios.
    
    Args:
        nombre: Título de la alerta
        descripcion: Descripción detallada
        prioridad: Nivel de prioridad (alta, media, baja)
        datos: Datos adicionales
        chat_id: ID del chat específico (opcional, si no se consulta config)
        nombre_nora: Nombre del cliente (para filtrar destinatarios)
        job_name: Nombre del job que genera la alerta
        tipo_alerta: Tipo de alerta específico
        
    Returns:
        True si se envió al menos una notificación exitosamente
    """
    notifier = TelegramNotifier()
    
    # Si se especifica chat_id directo, enviar solo a ese
    if chat_id:
        return notifier.enviar_alerta(
            nombre=nombre,
            descripcion=descripcion,
            prioridad=prioridad,
            datos=datos,
            chat_id=chat_id
        )
    
    # Si no, consultar configuración de destinatarios
    try:
        from automation_hub.db.supabase_client import create_client_from_env
        from automation_hub.db.repositories.telegram_config_repo import fetch_destinatarios_telegram
        
        supabase = create_client_from_env()
        destinatarios = fetch_destinatarios_telegram(
            supabase=supabase,
            nombre_nora=nombre_nora,
            job_name=job_name,
            prioridad=prioridad,
            tipo_alerta=tipo_alerta
        )
        
        if not destinatarios:
            logger.warning(f"No hay destinatarios configurados para: nora={nombre_nora}, job={job_name}, prioridad={prioridad}")
            # Enviar al chat_id por defecto como fallback
            return notifier.enviar_alerta(
                nombre=nombre,
                descripcion=descripcion,
                prioridad=prioridad,
                datos=datos
            )
        
        # Enviar a todos los destinatarios configurados
        exitos = 0
        for dest in destinatarios:
            dest_chat_id = dest.get("chat_id")
            nombre_contacto = dest.get("nombre_contacto", dest_chat_id)
            
            if notifier.enviar_alerta(
                nombre=nombre,
                descripcion=descripcion,
                prioridad=prioridad,
                datos=datos,
                chat_id=dest_chat_id
            ):
                logger.debug(f"Notificación enviada a {nombre_contacto}")
                exitos += 1
            else:
                logger.warning(f"No se pudo enviar a {nombre_contacto}")
        
        return exitos > 0
        
    except Exception as e:
        logger.error(f"Error consultando configuración de Telegram: {e}")
        # Fallback: enviar al chat_id por defecto
        return notifier.enviar_alerta(
            nombre=nombre,
            descripcion=descripcion,
            prioridad=prioridad,
            datos=datos
        )
