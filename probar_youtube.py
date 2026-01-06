"""
Script para probar la conexión de YouTube
"""
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation_hub.db.supabase_client import get_supabase_client
from automation_hub.integrations.youtube import YouTubeService

def probar_youtube():
    """Prueba la integración de YouTube"""
    
    print("=" * 80)
    print("PRUEBA DE INTEGRACIÓN YOUTUBE SHORTS")
    print("=" * 80)
    
    supabase = get_supabase_client()
    youtube_service = YouTubeService(supabase)
    
    # Solicitar cliente_id
    cliente_id = input("\nIngresa el cliente_id (UUID): ").strip()
    
    if not cliente_id:
        print("❌ Cliente ID requerido")
        return
    
    # Verificar si está conectado
    print(f"\n🔍 Verificando conexión para cliente: {cliente_id}")
    
    if youtube_service.is_connected(cliente_id):
        print("✅ Cliente tiene YouTube conectado")
        
        # Listar canales
        canales = youtube_service.get_canales_conectados(cliente_id)
        print(f"\n📺 Canales conectados: {len(canales)}")
        
        for canal in canales:
            print(f"\n  - {canal['canal_titulo']}")
            print(f"    ID: {canal['canal_id']}")
            print(f"    Conectado: {canal['created_at']}")
    else:
        print("❌ Cliente NO tiene YouTube conectado")
        
        # Generar URL de conexión
        print("\n🔗 Genera una URL de conexión:")
        print("\nEjemplo:")
        print(f"http://localhost:8000/integraciones/youtube/connect?cliente_id={cliente_id}")
        
        opcion = input("\n¿Generar URL de autorización? (s/n): ").strip().lower()
        
        if opcion == 's':
            redirect_uri = input("Redirect URI [http://localhost:8000/integraciones/youtube/callback]: ").strip()
            redirect_uri = redirect_uri or "http://localhost:8000/integraciones/youtube/callback"
            
            auth_url = youtube_service.get_authorization_url(
                cliente_id=cliente_id,
                redirect_uri=redirect_uri
            )
            
            print("\n" + "=" * 80)
            print("URL DE AUTORIZACIÓN:")
            print("=" * 80)
            print(f"\n{auth_url}\n")
            print("⚠️  IMPORTANTE: Solo el OWNER del canal puede conectar")
            print("   Los permisos de Manager/Editor NO funcionan con APIs")
            print("=" * 80)

if __name__ == '__main__':
    probar_youtube()
