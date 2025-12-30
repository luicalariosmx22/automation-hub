"""
Script para verificar si el token de GBP está funcional.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.integrations.google.oauth import get_gbp_creds_from_env

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verificar_token_gbp():
    """Verifica si el token de GBP está funcional."""
    # Cargar variables de entorno
    load_dotenv()
    
    print("\n" + "="*60)
    print("VERIFICACIÓN DEL TOKEN DE GBP")
    print("="*60 + "\n")
    
    # Verificar variables de entorno
    print("📋 Verificando variables de entorno...")
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("GBP_REFRESH_TOKEN", "").strip()
    
    if not client_id:
        print("❌ GOOGLE_CLIENT_ID no configurado")
        return False
    else:
        print(f"✓ GOOGLE_CLIENT_ID: {client_id[:20]}...")
    
    if not client_secret:
        print("❌ GOOGLE_CLIENT_SECRET no configurado")
        return False
    else:
        print(f"✓ GOOGLE_CLIENT_SECRET: configurado ({len(client_secret)} caracteres)")
    
    if not refresh_token:
        print("❌ GBP_REFRESH_TOKEN no configurado")
        return False
    else:
        print(f"✓ GBP_REFRESH_TOKEN: configurado ({len(refresh_token)} caracteres)")
    
    # Intentar obtener y refrescar credenciales
    print("\n🔄 Intentando refrescar el token...")
    try:
        creds = get_gbp_creds_from_env()
        
        print("\n✅ TOKEN DE GBP FUNCIONAL")
        print(f"   - Access Token obtenido: {creds.token[:30]}...")
        print(f"   - Token válido: {creds.valid}")
        print(f"   - Token expirado: {creds.expired}")
        
        if creds.expiry:
            print(f"   - Expira en: {creds.expiry}")
        
        return True
        
    except ValueError as e:
        print(f"\n❌ ERROR DE CONFIGURACIÓN: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR AL REFRESCAR TOKEN: {e}")
        print("\nPosibles causas:")
        print("  1. El refresh token ha expirado o fue revocado")
        print("  2. El client_id/client_secret no corresponden al refresh token")
        print("  3. Problemas de conectividad con Google OAuth")
        print("  4. El proyecto de Google Cloud no tiene la API habilitada")
        return False


if __name__ == "__main__":
    try:
        success = verificar_token_gbp()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
