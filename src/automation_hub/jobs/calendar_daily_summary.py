"""
Job para enviar resumen diario de citas por Telegram.

Envía a las 9 AM un resumen con todas las citas del día a todo el equipo.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, cast
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env si existe
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from automation_hub.config.logging import setup_logging
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import TelegramNotifier
from automation_hub.integrations.google_calendar.sync_service import GoogleCalendarSyncService
import os

logger = logging.getLogger(__name__)


def run():
    """Envía resumen diario de citas por Telegram."""
    setup_logging()
    logger.info("=== Iniciando resumen diario de citas ===")
    
    try:
        nombre_nora = os.getenv("NOMBRE_NORA", "aura")
        supabase = create_client_from_env()
        
        # Obtener fecha de hoy en timezone de Hermosillo
        import pytz
        hermosillo_tz = pytz.timezone('America/Hermosillo')
        ahora_hermosillo = datetime.now(hermosillo_tz)
        
        # PRIMERO: Sincronizar con Google Calendar para tener datos actualizados
        logger.info("Sincronizando con Google Calendar antes de generar resumen...")
        try:
            google_sync = GoogleCalendarSyncService(nombre_nora)
            status = google_sync.get_connection_status()
            
            if status.get('connected'):
                # Sincronizar solo el día de hoy (no necesitamos 60 días)
                inicio_sync = ahora_hermosillo.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
                fin_sync = ahora_hermosillo.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(timezone.utc)
                
                sync_stats = google_sync.sync_from_google(
                    inicio_sync.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    fin_sync.strftime('%Y-%m-%dT%H:%M:%SZ')
                )
                logger.info(f"Sync completado: {sync_stats}")
            else:
                logger.warning(f"Google Calendar no conectado: {status.get('reason')}")
        except Exception as e:
            logger.error(f"Error en sync de Google Calendar: {e}")
            # Continuamos aunque falle el sync
        
        # Inicio y fin del día en Hermosillo
        inicio_dia_hermosillo = ahora_hermosillo.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia_hermosillo = ahora_hermosillo.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Convertir a UTC para la query
        inicio_dia = inicio_dia_hermosillo.astimezone(timezone.utc)
        fin_dia = fin_dia_hermosillo.astimezone(timezone.utc)
        fin_dia = fin_dia_hermosillo.astimezone(timezone.utc)
        
        logger.info(f"Buscando citas para hoy en Hermosillo: {ahora_hermosillo.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Rango UTC: {inicio_dia.isoformat()} a {fin_dia.isoformat()}")
        
        # Consultar citas del día (no canceladas)
        result = supabase.table('agenda_citas') \
            .select('*') \
            .eq('nombre_nora', nombre_nora) \
            .gte('inicio', inicio_dia.isoformat()) \
            .lte('inicio', fin_dia.isoformat()) \
            .neq('estado', 'cancelada') \
            .order('inicio') \
            .execute()
        
        citas: List[Dict[str, Any]] = cast(List[Dict[str, Any]], result.data if result.data else [])
        
        logger.info(f"Encontradas {len(citas)} citas para hoy")
        
        # Formatear mensaje
        if not citas:
            mensaje = (
                f"📅 Agenda del día - {ahora_hermosillo.strftime('%d/%m/%Y')}\n\n"
                f"✨ No hay citas programadas para hoy\n\n"
                f"¡Buen día! 😊"
            )
        else:
            mensaje = (
                f"📅 Agenda del día - {ahora_hermosillo.strftime('%d/%m/%Y')}\n\n"
                f"📊 Total: {len(citas)} cita{'s' if len(citas) != 1 else ''}\n\n"
            )
            
            for i, cita in enumerate(citas, 1):
                # Parsear hora de inicio en UTC y convertir a Hermosillo
                inicio_utc = datetime.fromisoformat(cita['inicio'].replace('Z', '+00:00'))
                inicio_hermosillo = inicio_utc.astimezone(hermosillo_tz)
                hora = inicio_hermosillo.strftime('%H:%M')
                
                # Título
                titulo = cita.get('titulo', 'Sin título')
                
                # Cliente si existe
                cliente_id = cita.get('cliente_id')
                cliente_info = f" - Cliente: {cliente_id}" if cliente_id else ""
                
                # Meta información
                meta = cita.get('meta', {})
                extra_info = ''
                
                if isinstance(meta, dict):
                    # Ubicación
                    loc = meta.get('ubicacion', '')
                    if loc:
                        extra_info += f"\n   📍 {loc}"
                    
                    # Link de Google Meet
                    meet_link = meta.get('hangoutLink', '')
                    if meet_link:
                        extra_info += f"\n   🎥 {meet_link}"
                    
                    # Descripción (primeras 100 chars)
                    desc = meta.get('descripcion', '')
                    if desc:
                        desc_corta = desc[:100] + '...' if len(desc) > 100 else desc
                        extra_info += f"\n   📝 {desc_corta}"
                
                # Estado
                estado_emoji = {
                    'confirmada': '✅',
                    'pendiente': '⏳',
                    'cancelada': '❌'
                }.get(cita.get('estado', 'pendiente'), '⏳')
                
                mensaje += (
                    f"{i}. {estado_emoji} {hora} - {titulo}{cliente_info}{extra_info}\n"
                )
            
            mensaje += f"\n💼 ¡Que tengas un excelente día!"
        
        # Crear alerta
        crear_alerta(
            supabase=supabase,
            nombre="Resumen diario de citas",
            tipo="resumen_citas",
            nombre_nora=nombre_nora,
            descripcion=mensaje,
            prioridad="media",
            datos={
                "fecha": ahora_hermosillo.isoformat(),
                "total_citas": len(citas),
                "citas_ids": [c['id'] for c in citas]
            }
        )
        
        # Enviar a todo el equipo por Telegram usando bot de citas
        bot_token_citas = os.getenv("TELEGRAM_BOT_TOKEN_CITAS", "8556035050:AAF9guBOOEFnMjObUqTMpq-TtvpytUR-IZI")
        notifier = TelegramNotifier(bot_token=bot_token_citas)
        
        # Obtener destinatarios activos
        destinatarios_response = supabase.table('notificaciones_telegram_config') \
            .select('chat_id') \
            .eq('activo', True) \
            .execute()
        
        destinatarios = destinatarios_response.data or []
        
        if destinatarios:
            for dest in destinatarios:
                chat_id = dest.get('chat_id')
                notifier.enviar_mensaje(mensaje, chat_id=chat_id)
                logger.info(f"Resumen enviado a chat {chat_id}")
        else:
            # Fallback al chat por defecto
            notifier.enviar_mensaje(mensaje)
        
        logger.info(f"Resumen diario enviado: {len(citas)} citas")
        logger.info("=== Resumen diario de citas completado ===")
        
    except Exception as e:
        logger.error(f"Error en resumen diario de citas: {e}", exc_info=True)
        
        # Crear alerta de error
        try:
            supabase = create_client_from_env()
            nombre_nora = os.getenv("NOMBRE_NORA", "aura")
            
            mensaje_error = (
                f"❌ Error generando resumen diario de citas\n\n"
                f"Error: {str(e)}"
            )
            
            alerta = crear_alerta(
                supabase=supabase,
                nombre="Error en resumen diario de citas",
                tipo="error_sistema",
                nombre_nora=nombre_nora,
                descripcion=mensaje_error,
                prioridad="media",
                datos={"error": str(e), "job": "calendar.daily.summary"}
            )
            
            bot_token_citas = os.getenv("TELEGRAM_BOT_TOKEN_CITAS", "8556035050:AAF9guBOOEFnMjObUqTMpq-TtvpytUR-IZI")
            notifier = TelegramNotifier(bot_token=bot_token_citas)
            notifier.enviar_mensaje(mensaje_error)
        except:
            pass
        
        raise


if __name__ == "__main__":
    run()
