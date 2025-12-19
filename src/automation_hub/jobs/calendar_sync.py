"""
Job para sincronizar eventos de Google Calendar.

Sincroniza eventos del calendario de Google con la tabla agenda_citas cada 30 minutos.
"""
import logging
from datetime import datetime, timedelta, timezone
from automation_hub.config.logging import setup_logging
from automation_hub.integrations.google_calendar.sync_service import GoogleCalendarSyncService
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import TelegramNotifier
import os

logger = logging.getLogger(__name__)


def run():
    """Sincroniza eventos de Google Calendar con agenda_citas."""
    setup_logging()
    logger.info("=== Iniciando sincronización de Google Calendar ===")
    
    try:
        nombre_nora = os.getenv("NOMBRE_NORA", "aura")
        
        # Inicializar servicio de Google Calendar
        calendar_service = GoogleCalendarSyncService(nombre_nora)
        
        # Verificar conexión
        status = calendar_service.get_connection_status()
        if not status.get('connected'):
            logger.warning(f"Google Calendar no conectado: {status.get('reason')}")
            return
        
        logger.info(f"Google Calendar conectado: {status.get('user_email')}")
        
        # Sincronizar próximos 60 días
        fecha_desde = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_hasta = fecha_desde + timedelta(days=60)
        
        fecha_desde_str = fecha_desde.isoformat().replace('+00:00', 'Z')
        fecha_hasta_str = fecha_hasta.isoformat().replace('+00:00', 'Z')
        
        logger.info(f"Sincronizando eventos desde {fecha_desde_str} hasta {fecha_hasta_str}")
        
        # Ejecutar sincronización
        stats = calendar_service.sync_from_google(fecha_desde_str, fecha_hasta_str)
        
        logger.info(
            f"Sincronización completada: {stats['imported']} importadas, "
            f"{stats['updated']} actualizadas, {stats['cancelled']} canceladas, "
            f"{stats['errors']} errores"
        )
        
        # Si hay cambios significativos, enviar notificación
        if stats['imported'] > 0 or stats['cancelled'] > 0:
            supabase = create_client_from_env()
            
            mensaje = (
                f"📅 Sincronización de Google Calendar\n\n"
                f"✅ Nuevas: {stats['imported']}\n"
                f"🔄 Actualizadas: {stats['updated']}\n"
            )
            
            if stats['cancelled'] > 0:
                mensaje += f"❌ Canceladas: {stats['cancelled']}\n"
            
            if stats['errors'] > 0:
                mensaje += f"⚠️ Errores: {stats['errors']}\n"
            
            # Crear alerta
            crear_alerta(
                supabase=supabase,
                nombre="Sincronización Google Calendar",
                tipo="info_calendario",
                nombre_nora=nombre_nora,
                descripcion=mensaje,
                prioridad="baja",
                datos={
                    "stats": stats,
                    "fecha_desde": fecha_desde_str,
                    "fecha_hasta": fecha_hasta_str
                }
            )
            
            # Enviar notificación
            notifier = TelegramNotifier()
            notifier.enviar_mensaje(mensaje, disable_notification=True)
        
        logger.info("=== Sincronización de Google Calendar completada ===")
        
    except FileNotFoundError as e:
        logger.error(f"Error de configuración: {e}")
        logger.error("Google Calendar no está configurado correctamente")
        
    except Exception as e:
        logger.error(f"Error en sincronización de calendario: {e}", exc_info=True)
        
        # Crear alerta de error
        try:
            supabase = create_client_from_env()
            nombre_nora = os.getenv("NOMBRE_NORA", "aura")
            
            mensaje_error = (
                f"❌ Error en sincronización de Google Calendar\n\n"
                f"Error: {str(e)}"
            )
            
            alerta = crear_alerta(
                supabase=supabase,
                nombre="Error en sincronización Google Calendar",
                tipo="error_sistema",
                nombre_nora=nombre_nora,
                descripcion=mensaje_error,
                prioridad="media",
                datos={"error": str(e), "job": "calendar.sync"}
            )
            
            notifier = TelegramNotifier()
            notifier.enviar_mensaje(mensaje_error)
        except:
            pass
        
        raise


if __name__ == "__main__":
    run()
