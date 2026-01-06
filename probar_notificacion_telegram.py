#!/usr/bin/env python3
"""
Script para probar la notificación de Telegram
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
from datetime import datetime
from automation_hub.integrations.telegram.notifier import TelegramNotifier

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def probar_notificacion():
    """Probar envío de notificación de Telegram mejorada"""
    logger.info("🔔 Probando notificación de Telegram mejorada")
    
    try:
        telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
        
        # Simular una notificación de publicación exitosa con imagen REAL
        ubicacion_nombre = "Top Láser Hermosillo Centro"
        post_id = "TEST_123456789"
        mensaje = "Esta es una prueba de notificación mejorada para publicación exitosa en Google Business Profile"
        # URL real de imagen de Supabase que ya procesamos
        imagen_url = "https://sylqljdiiyhtgtrghwjk.supabase.co/storage/v1/object/public/meta-webhooks/aura/feed/photos/2025/12/116707543052879_1490600959735984_1767168642.jpg"
        
        # Mensaje más conciso como en el job real
        mensaje_corto = mensaje[:50] + "..." if len(mensaje) > 50 else mensaje
        
        mensaje_notif = f"""✅ **PUBLICACIÓN EXITOSA EN GBP** (PRUEBA)

📍 **{ubicacion_nombre}**
📝 "{mensaje_corto}"
⏰ {datetime.now().strftime('%H:%M')} • `{post_id}`

🧪 *Prueba del sistema mejorado*"""
        
        # Probar envío con imagen
        try:
            telegram.enviar_imagen(imagen_url, mensaje_notif)
            print("✅ Notificación con imagen enviada exitosamente!")
        except:
            # Fallback a solo texto si falla la imagen
            telegram.enviar_mensaje(mensaje_notif)
            print("✅ Notificación (solo texto) enviada exitosamente!")
        
        print("📱 Revisa tu Telegram para ver la notificación mejorada")
        
    except Exception as e:
        print(f"❌ Error enviando notificación: {e}")
        logger.error(f"Error enviando notificación: {e}")

if __name__ == "__main__":
    probar_notificacion()