"""
Script de prueba para enviar alerta de cuenta desactivada por WhatsApp y Telegram.
"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

import logging
from datetime import datetime
from automation_hub.integrations.telegram.notifier import TelegramNotifier
import requests
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def enviar_alerta_whatsapp(phone: str, message: str, title: str = "Alerta"):
    """Envía una alerta por WhatsApp."""
    try:
        whatsapp_url = os.getenv("WHATSAPP_SERVER_URL", "http://192.168.68.68:3000/send-alert")
        
        payload = {
            "phone": phone,
            "title": title,
            "message": message
        }
        
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(whatsapp_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ WhatsApp enviado a {phone}")
            return True
        else:
            logger.warning(f"⚠️  Error enviando WhatsApp: {response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️  Error enviando WhatsApp: {e}")
        return False


def test_alerta_cuenta_desactivada():
    """Prueba de alerta de cuenta desactivada."""
    print("=" * 80)
    print("🧪 TEST - Alerta de Cuenta Desactivada")
    print("=" * 80)
    print()
    
    # Datos de prueba
    nombre_cuenta = "Cuenta de Prueba - Nora AI"
    empresa_nombre = "Nora AI"
    id_cuenta_publicitaria = "act_1234567890"
    
    # 1. TELEGRAM
    try:
        print("📱 Enviando por Telegram...")
        telegram = TelegramNotifier(bot_nombre="Bot Principal")
        
        mensaje_telegram = f"""🚨 Cuenta Meta Ads Desactivada

La cuenta '{nombre_cuenta}' de {empresa_nombre} ha sido DESACTIVADA.

Esto puede deberse a:
• Problemas de pago
• Incumplimiento de políticas
• Límites de gasto alcanzados

Cuenta: {nombre_cuenta}
ID: {id_cuenta_publicitaria}
Cliente: {empresa_nombre}
Estado Anterior: Activa
Estado Actual: 2 (DESACTIVADA)

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
        
        telegram.enviar_mensaje(mensaje_telegram)
        print("✅ Telegram enviado\n")
    except Exception as e:
        print(f"❌ Error en Telegram: {e}\n")
    
    # 2. WHATSAPP
    try:
        print("📱 Enviando por WhatsApp...")
        whatsapp_phone = os.getenv("WHATSAPP_ALERT_PHONE", "5216629360887")
        
        mensaje_whatsapp = f"""🚨 Cuenta Meta Ads Desactivada

📊 {nombre_cuenta}
🏢 {empresa_nombre}
🆔 {id_cuenta_publicitaria}

⚠️ Esto puede deberse a:
• Problemas de pago
• Incumplimiento de políticas
• Límites de gasto alcanzados

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
        
        enviar_alerta_whatsapp(
            phone=whatsapp_phone,
            title="🚨 Cuenta Desactivada",
            message=mensaje_whatsapp
        )
        print("✅ WhatsApp enviado\n")
    except Exception as e:
        print(f"❌ Error en WhatsApp: {e}\n")
    
    print("=" * 80)
    print("✅ PRUEBA COMPLETADA")
    print("   Verifica que hayas recibido ambas notificaciones")
    print("=" * 80)


def test_alerta_nueva_pagina():
    """Prueba de alerta de nueva página de Facebook."""
    print("=" * 80)
    print("🧪 TEST - Alerta de Nueva Página de Facebook")
    print("=" * 80)
    print()
    
    # Datos de prueba
    page_name = "Página de Prueba - Nora AI"
    page_id = "123456789012345"
    category = "Empresa de Software"
    
    # 1. TELEGRAM
    try:
        print("📱 Enviando por Telegram...")
        telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
        
        mensaje_telegram = f"""🆕 **Nueva página de Facebook detectada**

📄 **{page_name}**
🆔 ID: {page_id}
📁 Categoría: {category}
✅ Publicada: Sí

⚠️ **Acción requerida:** 
- Vincular a una empresa en `cliente_empresas`
- Activar `publicar_en_gbp` si se desea sincronizar con Google Business Profile

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
        
        telegram.enviar_mensaje(mensaje_telegram)
        print("✅ Telegram enviado\n")
    except Exception as e:
        print(f"❌ Error en Telegram: {e}\n")
    
    # 2. WHATSAPP
    try:
        print("📱 Enviando por WhatsApp...")
        whatsapp_phone = os.getenv("WHATSAPP_ALERT_PHONE", "5216629360887")
        
        enviar_alerta_whatsapp(
            phone=whatsapp_phone,
            title="Nueva Página Facebook",
            message=mensaje_telegram
        )
        print("✅ WhatsApp enviado\n")
    except Exception as e:
        print(f"❌ Error en WhatsApp: {e}\n")
    
    print("=" * 80)
    print("✅ PRUEBA COMPLETADA")
    print("   Verifica que hayas recibido ambas notificaciones")
    print("=" * 80)


if __name__ == "__main__":
    print()
    print("Selecciona qué quieres probar:")
    print("  1. Alerta de cuenta desactivada")
    print("  2. Alerta de nueva página de Facebook")
    print("  3. Ambas")
    print()
    
    opcion = input("Opción (1/2/3): ").strip()
    print()
    
    if opcion == "1":
        test_alerta_cuenta_desactivada()
    elif opcion == "2":
        test_alerta_nueva_pagina()
    elif opcion == "3":
        test_alerta_cuenta_desactivada()
        print("\n" * 2)
        test_alerta_nueva_pagina()
    else:
        print("Opción inválida")
