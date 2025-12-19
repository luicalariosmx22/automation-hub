"""
Script helper para configurar el bot de Telegram.

Instrucciones:
1. Abre Telegram y busca @BotFather
2. Envía /newbot y sigue las instrucciones
3. Copia el token que te da
4. Pega el token aquí y ejecuta este script
5. Envía un mensaje a tu bot
6. El script te dirá tu chat_id
7. Agrega ambos valores al archivo .env
"""
import sys
import requests


def obtener_chat_id(bot_token: str):
    """Obtiene el chat_id del último mensaje recibido por el bot."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ok"):
            print(f"❌ Error: {data}")
            return None
        
        updates = data.get("result", [])
        if not updates:
            print("⚠️  No hay mensajes aún.")
            print("👉 Envía un mensaje a tu bot en Telegram y vuelve a ejecutar este script.")
            return None
        
        # Obtener el último mensaje
        last_update = updates[-1]
        chat_id = last_update.get("message", {}).get("chat", {}).get("id")
        chat_name = last_update.get("message", {}).get("chat", {}).get("first_name", "")
        
        if chat_id:
            print(f"✅ Chat ID encontrado: {chat_id}")
            print(f"👤 Usuario: {chat_name}")
            print("\n📝 Agrega estas variables a tu archivo .env:")
            print(f"TELEGRAM_BOT_TOKEN={bot_token}")
            print(f"TELEGRAM_CHAT_ID={chat_id}")
            return chat_id
        else:
            print("❌ No se pudo extraer el chat_id")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def enviar_mensaje_prueba(bot_token: str, chat_id: str):
    """Envía un mensaje de prueba al chat."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🎉 <b>Bot configurado correctamente!</b>\n\nRecibirás notificaciones de alertas aquí.",
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        if response.json().get("ok"):
            print("\n✅ Mensaje de prueba enviado correctamente!")
            return True
        else:
            print(f"\n❌ Error enviando mensaje: {response.json()}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🤖 Configurador de Bot de Telegram\n")
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = input("Pega el token de tu bot (de @BotFather): ").strip()
    
    if not token:
        print("❌ Token vacío")
        sys.exit(1)
    
    print(f"\n🔍 Buscando mensajes...")
    chat_id = obtener_chat_id(token)
    
    if chat_id:
        respuesta = input("\n¿Enviar mensaje de prueba? (s/n): ").strip().lower()
        if respuesta == 's':
            enviar_mensaje_prueba(token, str(chat_id))
