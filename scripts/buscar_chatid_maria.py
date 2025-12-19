"""Script para obtener el chat_id de Maria Jesus"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

print("🔍 Buscando chat_id de Maria Jesus...\n")
print("Instrucciones:")
print("1. Maria Jesus debe enviar /start al bot @soynoraai_alerts_bot")
print("2. Luego este script mostrará su chat_id\n")

# Obtener actualizaciones del bot
url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    
    if data.get('result'):
        print(f"💬 Mensajes recientes del bot:\n")
        
        chats_vistos = set()
        for update in reversed(data['result'][-10:]):  # Últimos 10 mensajes
            if 'message' in update:
                msg = update['message']
                chat = msg.get('chat', {})
                chat_id = chat.get('id')
                first_name = chat.get('first_name', '')
                last_name = chat.get('last_name', '')
                username = chat.get('username', '')
                text = msg.get('text', '')
                
                if chat_id and chat_id not in chats_vistos:
                    chats_vistos.add(chat_id)
                    nombre_completo = f"{first_name} {last_name}".strip()
                    print(f"👤 {nombre_completo}")
                    if username:
                        print(f"   @{username}")
                    print(f"   Chat ID: {chat_id}")
                    print(f"   Mensaje: {text}")
                    print()
        
        if not chats_vistos:
            print("⚠️ No se encontraron mensajes recientes")
            print("Maria Jesus debe enviar /start al bot primero")
    else:
        print("⚠️ No hay mensajes en el bot todavía")
        print("Maria Jesus debe enviar /start a @soynoraai_alerts_bot")
else:
    print(f"❌ Error al consultar el bot: {response.status_code}")

print("\n" + "="*60)
print("Una vez que tengas el chat_id de Maria Jesus, ejecuta:")
print("python scripts/agregar_maria_jesus_con_chatid.py <CHAT_ID>")
