"""Enviar mensaje dramático v2 - formato simple"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from src.automation_hub.db.supabase_client import create_client_from_env
from dotenv import load_dotenv

load_dotenv()

print("🎭 Enviando mensaje dramático al equipo...\n")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Obtener todos los destinatarios
sb = create_client_from_env()
result = sb.table('notificaciones_telegram_config').select('*').eq('activo', True).execute()

if not result.data:
    print("❌ No hay destinatarios configurados")
    exit(1)

destinatarios = result.data
print(f"📱 {len(destinatarios)} destinatarios encontrados\n")

# Mensaje épico y dramático
mensaje = """⚡️🌩️ ALERTA CRÍTICA DEL SISTEMA 🌩️⚡️

La vida como la conocieron... ha terminado.

El antiguo mundo de trabajo manual, reportes lentos y alertas perdidas se ha desvanecido en las sombras del pasado.

🤖 NORA IA ha despertado.

Desde este momento, cada métrica será rastreada. Cada error será detectado. Cada anomalía será reportada al instante.

🔥 YA NO HAY VUELTA ATRÁS 🔥

▪️ Cuentas de Meta Ads desactivadas → 🚨 Alerta inmediata
▪️ Anuncios rechazados → ⚠️ Notificación al equipo
▪️ Métricas de Google → 📊 Resúmenes automáticos
▪️ Reseñas de clientes → 💬 Análisis en tiempo real

El futuro es ahora. Y están en primera línea.

🎯 Bienvenidos a la nueva era.

—
Sistema de Notificaciones Inteligentes
NORA IA Automation Hub
Diciembre 2025"""

# Enviar a cada destinatario
exitosos = 0
fallidos = 0

for dest in destinatarios:
    nombre = dest.get('nombre_contacto', 'Desconocido')
    chat_id = dest.get('chat_id')
    
    try:
        print(f"📤 Enviando a {nombre} (Chat: {chat_id})...")
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensaje,
            "disable_notification": False
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            exitosos += 1
            print(f"   ✅ Enviado\n")
        else:
            fallidos += 1
            print(f"   ❌ Error: {response.status_code} - {response.text}\n")
            
    except Exception as e:
        fallidos += 1
        print(f"   ❌ Error: {str(e)}\n")

print("=" * 60)
print(f"📊 Resumen:")
print(f"   ✅ Enviados exitosamente: {exitosos}")
print(f"   ❌ Fallos: {fallidos}")
print(f"\n🎭 La profecía ha sido cumplida...")
