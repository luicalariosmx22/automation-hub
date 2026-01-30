"""Test para verificar si el token de GBP funciona"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from automation_hub.integrations.google.oauth import get_gbp_creds_from_env

try:
    print("🔄 Intentando refrescar token de GBP...")
    creds = get_gbp_creds_from_env()
    print(f"✅ Token válido obtenido")
    print(f"📝 Access token (primeros 50 chars): {creds.token[:50]}...")
    print(f"🔑 Refresh token en uso: {creds.refresh_token[:30]}...")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
