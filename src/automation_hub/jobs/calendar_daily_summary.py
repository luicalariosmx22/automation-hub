"""
Job para enviar resumen diario de citas por Telegram.

Envía a las 9 AM un resumen con todas las citas del día a todo el equipo.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from automation_hub.config.logging import setup_logging
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import TelegramNotifier
import os

logger = logging.getLogger(__name__)


def run():
    """Envía resumen diario de citas por Telegram."""
    setup_logging()
    logger.info("=== Iniciando resumen diario de citas ===")
    
    try:
        nombre_nora = os.getenv("NOMBRE_NORA", "aura")
        supabase = create_client_from_env()
        
        # Obtener fecha de hoy
        hoy = datetime.now(timezone.utc)
        inicio_dia = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Consultar citas del día (no canceladas)
        result = supabase.table('agenda_citas') \
            .select('*') \
            .eq('nombre_nora', nombre_nora) \
            .gte('inicio', inicio_dia.isoformat()) \
            .lte('inicio', fin_dia.isoformat()) \
            .neq('estado', 'cancelada') \
            .order('inicio') \
            .execute()
        
        citas: List[Dict[str, Any]] = result.data if result.data else []
        
        logger.info(f"Encontradas {len(citas)} citas para hoy")
        
        # Formatear mensaje
        if not citas:
            mensaje = (
                f"📅 Agenda del día - {hoy.strftime('%d/%m/%Y')}\n\n"
                f"✨ No hay citas programadas para hoy\n\n"
                f"¡Buen día! 😊"
            )
        else:
            mensaje = (
                f"📅 Agenda del día - {hoy.strftime('%d/%m/%Y')}\n\n"
                f"📊 Total: {len(citas)} cita{'s' if len(citas) != 1 else ''}\n\n"
            )
            
            for i, cita in enumerate(citas, 1):
                # Parsear hora de inicio
                inicio = datetime.fromisoformat(cita['inicio'].replace('Z', '+00:00'))
                hora = inicio.strftime('%H:%M')
                
                # Título
                titulo = cita.get('titulo', 'Sin título')
                
                # Cliente si existe
                cliente_id = cita.get('cliente_id')
                cliente_info = f" - Cliente: {cliente_id}" if cliente_id else ""
                
                # Ubicación si existe
                meta = cita.get('meta', {})
                ubicacion = ''
                if isinstance(meta, dict):
                    loc = meta.get('ubicacion', '')
                    if loc:
                        ubicacion = f"\n   📍 {loc}"
                
                # Estado
                estado_emoji = {
                    'confirmada': '✅',
                    'pendiente': '⏳',
                    'cancelada': '❌'
                }.get(cita.get('estado', 'pendiente'), '⏳')
                
                mensaje += (
                    f"{i}. {estado_emoji} {hora} - {titulo}{cliente_info}{ubicacion}\n"
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
                "fecha": hoy.isoformat(),
                "total_citas": len(citas),
                "citas_ids": [c['id'] for c in citas]
            }
        )
        
        # Enviar a todo el equipo por Telegram
        notifier = TelegramNotifier()
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
            
            notifier = TelegramNotifier()
            notifier.enviar_mensaje(mensaje_error)
        except:
            pass
        
        raise


if __name__ == "__main__":
    run()
