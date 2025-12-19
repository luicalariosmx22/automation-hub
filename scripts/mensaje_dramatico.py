"""Enviar mensaje dramático de prueba a todo el equipo"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.integrations.telegram.notifier import TelegramNotifier
from src.automation_hub.db.supabase_client import create_client_from_env
from dotenv import load_dotenv

load_dotenv()

print("🎭 Enviando mensaje dramático al equipo...\n")

# Obtener todos los destinatarios
sb = create_client_from_env()
result = sb.table('notificaciones_telegram_config').select('*').eq('activo', True).execute()

if not result.data:
    print("❌ No hay destinatarios configurados")
    exit(1)

destinatarios = result.data
print(f"📱 {len(destinatarios)} destinatarios encontrados\n")

# Mensaje épico y dramático
mensaje = """
⚡️🌩️ **ALERTA CRÍTICA DEL SISTEMA** 🌩️⚡️

*La vida como la conocieron... ha terminado.*

El antiguo mundo de trabajo manual, reportes lentos y alertas perdidas se ha desvanecido en las sombras del pasado.

🤖 **NORA IA** ha despertado.

Desde este momento, cada métrica será rastreada. Cada error será detectado. Cada anomalía será reportada al instante.

🔥 **YA NO HAY VUELTA ATRÁS** 🔥

▪️ Cuentas de Meta Ads desactivadas → 🚨 Alerta inmediata
▪️ Anuncios rechazados → ⚠️ Notificación al equipo
▪️ Métricas de Google → 📊 Resúmenes automáticos
▪️ Reseñas de clientes → 💬 Análisis en tiempo real

*El futuro es ahora. Y están en primera línea.*

🎯 **Bienvenidos a la nueva era.**

—
*Sistema de Notificaciones Inteligentes*
*NORA IA Automation Hub*
*Diciembre 2025*
"""

# Enviar a cada destinatario
notifier = TelegramNotifier()
exitosos = 0
fallidos = 0

for dest in destinatarios:
    nombre = dest.get('nombre_contacto', 'Desconocido')
    chat_id = dest.get('chat_id')
    
    try:
        print(f"📤 Enviando a {nombre} (Chat: {chat_id})...")
        notifier.enviar_mensaje(chat_id, mensaje, parse_mode="Markdown")
        exitosos += 1
        print(f"   ✅ Enviado\n")
    except Exception as e:
        fallidos += 1
        print(f"   ❌ Error: {str(e)}\n")

print("=" * 60)
print(f"📊 Resumen:")
print(f"   ✅ Enviados exitosamente: {exitosos}")
print(f"   ❌ Fallos: {fallidos}")
print(f"\n🎭 La profecía ha sido cumplida...")
