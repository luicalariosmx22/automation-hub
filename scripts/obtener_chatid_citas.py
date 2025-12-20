"""
Script para obtener el chat_id del bot de citas
Después de enviar /start al bot, ejecuta este script para ver tu chat_id
"""
import requests

BOT_TOKEN = "8556035050:AAF9guBOOEFnMjObUqTMpq-TtvpytUR-IZI"

def obtener_updates():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("ok"):
            print(f"❌ Error: {data}")
            return
        
        updates = data.get("result", [])
        
        if not updates:
            print("⚠️  No hay mensajes nuevos")
            print("\nPasos:")
            print("1. Busca @AuraAgendaBot (o el nombre de tu bot) en Telegram")
            print("2. Envíale el mensaje: /start")
            print("3. Ejecuta este script de nuevo")
            return
        
        print("\n" + "="*80)
        print("CHAT IDs DISPONIBLES:")
        print("="*80 + "\n")
        
        chat_ids_vistos = set()
        
        for update in updates:
            message = update.get("message", {})
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            
            if chat_id and chat_id not in chat_ids_vistos:
                chat_ids_vistos.add(chat_id)
                
                first_name = chat.get("first_name", "")
                last_name = chat.get("last_name", "")
                username = chat.get("username", "")
                
                nombre_completo = f"{first_name} {last_name}".strip()
                
                print(f"👤 {nombre_completo}")
                if username:
                    print(f"   @{username}")
                print(f"   Chat ID: {chat_id}")
                print()
        
        print("="*80)
        print("\nPara configurar estos chat_ids, agrégalos a:")
        print("notificaciones_telegram_config en Supabase")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    obtener_updates()
