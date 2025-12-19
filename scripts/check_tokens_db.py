"""Script para verificar tokens en la tabla google_calendar_sync."""
import os
from automation_hub.db.supabase_client import create_client_from_env

def main():
    supabase = create_client_from_env()
    
    print("🔍 Verificando tokens en google_calendar_sync...\n")
    
    result = supabase.table('google_calendar_sync').select('*').execute()
    
    if not result.data:
        print("❌ No hay registros en google_calendar_sync")
        print("\n💡 Solución:")
        print("   1. Ve a: https://app.soynoraai.com")
        print("   2. Desconecta Google Calendar")
        print("   3. Vuelve a conectar y autoriza")
        return
    
    print(f"📊 Encontrados {len(result.data)} registro(s):\n")
    
    for row in result.data:
        nombre_nora = row.get('nombre_nora', 'N/A')
        user_email = row.get('user_email', 'N/A')
        expires_at = row.get('expires_at', 'N/A')
        selected_calendar = row.get('selected_calendar_id', 'N/A')
        has_access = '✅' if row.get('access_token') else '❌'
        has_refresh = '✅' if row.get('refresh_token') else '❌'
        
        print(f"  • nombre_nora: {nombre_nora}")
        print(f"    Email: {user_email}")
        print(f"    Calendario: {selected_calendar}")
        print(f"    Access Token: {has_access}")
        print(f"    Refresh Token: {has_refresh}")
        print(f"    Expira: {expires_at}")
        print()

if __name__ == "__main__":
    main()
