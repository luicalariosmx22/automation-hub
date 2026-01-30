"""
Script de prueba para enviar mensaje de alerta por WhatsApp.
Prueba el webhook server de WhatsApp antes de integrarlo con las alertas del sistema.
"""
import requests
import json
import sys

# Configuración del servidor WhatsApp
WHATSAPP_SERVER_URL = "http://192.168.68.68:3000/send-alert"
# WHATSAPP_SERVER_URL = "http://localhost:3000/send-alert"  # Si el servidor está en la misma computadora

# Número de teléfono de prueba
# Formato: código país + número (sin espacios, sin +)
TEST_PHONE = "5216629360887"  # Tu número de WhatsApp

# Mensaje de prueba
TEST_MESSAGE = """📅 Prueba de alerta de calendario

✅ Este es un mensaje de prueba
⏰ Hora: 9:00 AM
📍 Ubicación: Test
🎥 Meet: https://meet.google.com/test

💼 Sistema funcionando correctamente"""


def enviar_alerta_whatsapp(phone: str, message: str, server_url: str = WHATSAPP_SERVER_URL):
    """Envía una alerta por WhatsApp."""
    try:
        print(f"📱 Enviando mensaje a: {phone}")
        print(f"🌐 Servidor: {server_url}")
        print(f"📝 Mensaje:\n{message}\n")
        
        payload = {
            "phone": phone,
            "message": message
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Si tienes un token de autorización, agrégalo aquí
        # token = "tu-token-secreto-aqui"
        # headers["Authorization"] = f"Bearer {token}"
        
        response = requests.post(
            server_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Respuesta: {response.text}\n")
        
        if response.status_code == 200:
            print("✅ Mensaje enviado exitosamente")
            try:
                data = response.json()
                print(f"📦 Data: {json.dumps(data, indent=2)}")
            except:
                pass
            return True
        else:
            print(f"❌ Error al enviar mensaje: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: No se pudo conectar al servidor WhatsApp")
        print("   Verifica que el servidor esté corriendo en el puerto 3000")
        print("   Ejecuta: node whatsapp-webhook-server.js")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout: El servidor no respondió a tiempo")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def verificar_servidor():
    """Verifica que el servidor WhatsApp esté corriendo."""
    try:
        print("🔍 Verificando servidor WhatsApp...")
        # Usar la misma URL base que para enviar mensajes
        base_url = WHATSAPP_SERVER_URL.replace("/send-alert", "")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            print("✅ Servidor WhatsApp está corriendo")
            try:
                data = response.json()
                print(f"📦 Info del servidor: {json.dumps(data, indent=2)}\n")
            except:
                pass
            return True
        else:
            print(f"⚠️  Servidor respondió con código {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Servidor WhatsApp NO está corriendo")
        print("   Ejecuta primero: node whatsapp-webhook-server.js\n")
        return False
    except Exception as e:
        print(f"❌ Error verificando servidor: {e}\n")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST - Alerta WhatsApp")
    print("=" * 60)
    print()
    
    # 1. Verificar servidor
    if not verificar_servidor():
        print("💡 Instrucciones:")
        print("   1. Navega a la carpeta del servidor WhatsApp")
        print("   2. Ejecuta: node whatsapp-webhook-server.js")
        print("   3. Espera a que escanees el código QR")
        print("   4. Vuelve a ejecutar este script")
        sys.exit(1)
    
    # 2. Permitir personalizar el número desde línea de comandos
    phone = TEST_PHONE
    if len(sys.argv) > 1:
        phone = sys.argv[1]
        print(f"📱 Usando número de teléfono: {phone}\n")
    else:
        print(f"⚠️  Usando número de prueba: {phone}")
        print(f"   Para usar otro número: python test_whatsapp_alert.py 5216621234567\n")
    
    # 3. Enviar mensaje de prueba
    exito = enviar_alerta_whatsapp(phone, TEST_MESSAGE)
    
    print()
    print("=" * 60)
    if exito:
        print("✅ PRUEBA EXITOSA")
        print("   El mensaje debería aparecer en WhatsApp")
    else:
        print("❌ PRUEBA FALLIDA")
        print("   Revisa los errores arriba")
    print("=" * 60)
