"""
Script para regenerar el token de OAuth de Google Business Profile.

Este script te guiará para:
1. Obtener un código de autorización de Google
2. Intercambiarlo por un nuevo refresh_token
3. Actualizar tu archivo .env con el nuevo token

Requisitos:
- Tener configurados GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en .env
- Acceso al navegador para autorizar la aplicación
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlencode
import requests

# Cargar variables de entorno
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')

# Scopes necesarios para Google Business Profile
SCOPES = [
    'https://www.googleapis.com/auth/business.manage',
]

def obtener_client_credentials():
    """Obtiene las credenciales del cliente desde .env"""
    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    
    if not client_id or not client_secret:
        print("❌ ERROR: GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET deben estar en .env")
        sys.exit(1)
    
    return client_id, client_secret


def generar_url_autorizacion(client_id: str) -> str:
    """Genera la URL de autorización de Google OAuth"""
    params = {
        'client_id': client_id,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',  # Importante para obtener refresh_token
        'prompt': 'consent',  # Forzar el consent screen
    }
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def intercambiar_codigo_por_token(code: str, client_id: str, client_secret: str) -> dict:
    """Intercambia el código de autorización por tokens"""
    token_url = 'https://oauth2.googleapis.com/token'
    
    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'authorization_code',
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    
    return response.json()


def actualizar_env_file(refresh_token: str):
    """Actualiza el archivo .env con el nuevo refresh_token"""
    env_path = root_dir / '.env'
    
    if not env_path.exists():
        print(f"❌ ERROR: No se encontró {env_path}")
        return False
    
    # Leer el archivo
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Buscar y reemplazar GBP_REFRESH_TOKEN
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('GBP_REFRESH_TOKEN='):
            lines[i] = f'GBP_REFRESH_TOKEN={refresh_token}\n'
            updated = True
            break
    
    # Si no existía, agregarlo
    if not updated:
        lines.append(f'\nGBP_REFRESH_TOKEN={refresh_token}\n')
    
    # Escribir de vuelta
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True


def main():
    """Función principal"""
    print("=" * 70)
    print("🔐 REGENERAR TOKEN DE GOOGLE BUSINESS PROFILE")
    print("=" * 70)
    print()
    
    # 1. Obtener credenciales
    client_id, client_secret = obtener_client_credentials()
    print(f"✓ Client ID: {client_id[:20]}...")
    print()
    
    # 2. Generar URL de autorización
    auth_url = generar_url_autorizacion(client_id)
    print("📋 PASO 1: Autorizar la aplicación")
    print("-" * 70)
    print("Abre esta URL en tu navegador:")
    print()
    print(auth_url)
    print()
    print("Autoriza la aplicación y Google te mostrará el código directamente.")
    print("Copia ese código.")
    print()
    
    # 3. Solicitar código
    print("-" * 70)
    code = input("📝 Pega aquí el código que te mostró Google: ").strip()
    
    if not code:
        print("❌ ERROR: No se proporcionó ningún código")
        sys.exit(1)
    
    # Limpiar el código (por si pegaron toda la URL)
    if 'code=' in code:
        code = code.split('code=')[1].split('&')[0]
    
    print()
    print("🔄 Intercambiando código por tokens...")
    
    try:
        # 4. Obtener tokens
        tokens = intercambiar_codigo_por_token(code, client_id, client_secret)
        
        refresh_token = tokens.get('refresh_token')
        access_token = tokens.get('access_token')
        
        if not refresh_token:
            print("❌ ERROR: No se recibió refresh_token")
            print("Esto puede ocurrir si ya autorizaste antes.")
            print("Intenta revocar el acceso en: https://myaccount.google.com/permissions")
            print("Y ejecuta este script nuevamente.")
            sys.exit(1)
        
        print("✓ Tokens obtenidos exitosamente")
        print()
        print("📋 RESULTADO:")
        print("-" * 70)
        print(f"Refresh Token: {refresh_token}")
        print(f"Access Token: {access_token[:20]}...")
        print()
        
        # 5. Actualizar .env
        respuesta = input("¿Actualizar archivo .env automáticamente? (s/n): ").strip().lower()
        
        if respuesta == 's':
            if actualizar_env_file(refresh_token):
                print("✓ Archivo .env actualizado exitosamente")
                print()
                print("🎉 ¡Listo! Ahora puedes ejecutar los jobs de GBP sin errores.")
            else:
                print("❌ No se pudo actualizar el archivo .env")
                print(f"Actualiza manualmente GBP_REFRESH_TOKEN={refresh_token}")
        else:
            print()
            print("📝 INSTRUCCIONES:")
            print("-" * 70)
            print("Agrega o actualiza esta línea en tu archivo .env:")
            print()
            print(f"GBP_REFRESH_TOKEN={refresh_token}")
            print()
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ ERROR HTTP: {e}")
        print(f"Respuesta: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
