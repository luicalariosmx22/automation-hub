"""
Script para diagnosticar problemas con Google OAuth
Ayuda a identificar por qué los refresh tokens fallan
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

def verificar_token_info(refresh_token, nombre):
    """Intenta obtener información sobre el token"""
    print(f"\n{'='*70}")
    print(f"🔍 DIAGNOSTICANDO: {nombre}")
    print(f"{'='*70}")
    
    # Intentar obtener info del token
    token_info_url = "https://oauth2.googleapis.com/tokeninfo"
    
    # Primero, intentamos refrescar el token para ver el error específico
    client_id = os.getenv("GOOGLE_CLIENT_ID") if "GBP" in nombre else os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") if "GBP" in nombre else os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    print(f"Client ID: {client_id[:30]}...")
    print(f"Refresh Token: {refresh_token[:30]}...")
    
    # Intentar refrescar
    refresh_url = "https://oauth2.googleapis.com/token"
    refresh_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(refresh_url, data=refresh_data, timeout=10)
        print(f"\n📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            access_token = result.get("access_token")
            print("✅ Token refrescado exitosamente!")
            print(f"Access Token obtenido: {access_token[:50]}...")
            print(f"Expires in: {result.get('expires_in')} segundos")
            print(f"Token Type: {result.get('token_type')}")
            if 'scope' in result:
                print(f"Scopes: {result.get('scope')}")
            
            # Ahora obtener info del access token
            info_response = requests.get(f"{token_info_url}?access_token={access_token}", timeout=10)
            if info_response.status_code == 200:
                info = info_response.json()
                print(f"\n📋 Token Info:")
                print(f"  - Issued to: {info.get('azp', 'N/A')}")
                print(f"  - User ID: {info.get('sub', 'N/A')}")
                print(f"  - Email: {info.get('email', 'N/A')}")
                print(f"  - Expires in: {info.get('expires_in', 'N/A')} segundos")
                print(f"  - Scopes: {info.get('scope', 'N/A')}")
                
        else:
            error = response.json()
            print(f"❌ Error: {error}")
            print(f"\n🔍 Diagnóstico:")
            
            error_type = error.get("error", "")
            error_desc = error.get("error_description", "")
            
            if error_type == "invalid_grant":
                print("⚠️  INVALID_GRANT - Posibles causas:")
                print("   1. Aplicación en modo 'Testing' (tokens expiran en 7 días)")
                print("   2. Usuario revocó el acceso manualmente")
                print("   3. Token excedió 6 meses sin uso")
                print("   4. Client ID/Secret no coinciden con el token")
                print("   5. Se alcanzó el límite de 50 tokens por usuario")
                print("\n💡 Solución:")
                print("   - Ve a Google Cloud Console")
                print("   - Verifica que tu app esté en modo 'Production' (no Testing)")
                print("   - Regenera el refresh token usando el flujo OAuth")
                
            elif error_type == "invalid_client":
                print("⚠️  INVALID_CLIENT - El Client ID/Secret son incorrectos")
                print("💡 Verifica tus credenciales en Google Cloud Console")
                
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

# Verificar ambos tokens
print("="*70)
print("🔬 DIAGNÓSTICO DE GOOGLE OAUTH TOKENS")
print("="*70)

gbp_token = os.getenv("GBP_REFRESH_TOKEN")
calendar_token = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN")

if gbp_token:
    verificar_token_info(gbp_token, "GBP (Google Business Profile)")
else:
    print("❌ GBP_REFRESH_TOKEN no encontrado en .env")

if calendar_token:
    verificar_token_info(calendar_token, "GOOGLE CALENDAR")
else:
    print("❌ GOOGLE_CALENDAR_REFRESH_TOKEN no encontrado en .env")

print("\n" + "="*70)
print("📚 RECURSOS ÚTILES:")
print("="*70)
print("1. Google Cloud Console: https://console.cloud.google.com/")
print("2. Verificar permisos: https://myaccount.google.com/permissions")
print("3. OAuth Playground: https://developers.google.com/oauthplayground/")
print("="*70)
