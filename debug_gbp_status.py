"""
Script simple para diagnosticar el job meta_to_gbp_daily.
"""
import os
import sys
sys.path.insert(0, 'src')

def main():
    print("🔍 DIAGNÓSTICO del job META → GBP")
    print("=" * 50)
    
    # 1. Verificar variables de entorno críticas
    print("\n📋 VARIABLES DE ENTORNO:")
    vars_to_check = [
        "SUPABASE_URL",
        "SUPABASE_KEY", 
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GBP_REFRESH_TOKEN"
    ]
    
    missing_vars = []
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            # Mostrar solo los primeros y últimos caracteres por seguridad
            if len(value) > 10:
                display = f"{value[:6]}...{value[-4:]}"
            else:
                display = "***"
            print(f"  ✅ {var}: {display}")
        else:
            print(f"  ❌ {var}: NO CONFIGURADO")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ FALTAN {len(missing_vars)} variables críticas")
        print("   Este script necesita variables de entorno para funcionar")
        print("   En Railway están configuradas, por eso funciona allí")
        return
    
    # 2. Probar conexión a Supabase
    print("\n🗄️ PROBANDO CONEXIÓN A SUPABASE:")
    try:
        from automation_hub.db.supabase_client import create_client_from_env
        supabase = create_client_from_env()
        print("  ✅ Conexión a Supabase exitosa")
        
        # 3. Contar publicaciones pendientes
        print("\n📊 PUBLICACIONES PENDIENTES PARA GBP:")
        response = supabase.table("meta_publicaciones_webhook")\
            .select("id", count="exact")\
            .eq("publicada_gbp", False)\
            .not_.is_("mensaje", "null")\
            .gte("creada_en", "2025-12-01")\
            .execute()
        
        total_pendientes = response.count or 0
        print(f"  📈 Total pendientes: {total_pendientes}")
        
        if total_pendientes == 0:
            print("  ⚠️ NO HAY PUBLICACIONES PENDIENTES")
            print("     Posibles razones:")
            print("     - Ya se publicaron todas")
            print("     - No hay posts con mensaje")
            print("     - No hay posts desde diciembre 2025")
        
        # 4. Verificar páginas configuradas para GBP
        print("\n🏢 PÁGINAS CONFIGURADAS PARA GBP:")
        response = supabase.table("facebook_paginas")\
            .select("page_id,nombre,publicar_en_gbp", count="exact")\
            .eq("publicar_en_gbp", True)\
            .execute()
        
        paginas_activas = response.count or 0
        print(f"  📈 Páginas activas: {paginas_activas}")
        
        if paginas_activas == 0:
            print("  ⚠️ NO HAY PÁGINAS CONFIGURADAS PARA GBP")
            print("     Necesitas activar 'publicar_en_gbp' en facebook_paginas")
        
        # 5. Verificar locaciones GBP
        print("\n📍 LOCACIONES GBP ACTIVAS:")
        response = supabase.table("gbp_locations")\
            .select("location_name", count="exact")\
            .eq("activa", True)\
            .execute()
        
        locaciones_activas = response.count or 0
        print(f"  📈 Locaciones activas: {locaciones_activas}")
        
        if locaciones_activas == 0:
            print("  ⚠️ NO HAY LOCACIONES GBP ACTIVAS")
            print("     Necesitas locaciones en gbp_locations con activa=true")
    
    except Exception as e:
        print(f"  ❌ Error conectando a Supabase: {e}")
        return
    
    # 6. Probar Google OAuth (si las variables existen)
    print("\n🔐 PROBANDO GOOGLE OAUTH:")
    try:
        from automation_hub.integrations.google.oauth import get_gbp_creds_from_env
        creds = get_gbp_creds_from_env()
        print("  ✅ Google OAuth tokens válidos")
        print(f"  🕐 Token expira: {creds.expiry}")
    except Exception as e:
        print(f"  ❌ Error Google OAuth: {e}")
        print("     ESTE ES EL PROBLEMA PRINCIPAL")
        print("     Necesitas renovar tokens en Railway:")
        print("     1. Ve a Google OAuth Playground")
        print("     2. Genera nuevo refresh_token")
        print("     3. Actualiza GBP_REFRESH_TOKEN en Railway")
    
    print("\n" + "=" * 50)
    print("🎯 CONCLUSIÓN:")
    
    if total_pendientes > 0 and paginas_activas > 0 and locaciones_activas > 0:
        print("  📝 HAY CONTENIDO PARA PUBLICAR")
        print("  🔑 PROBLEMA: Google OAuth tokens expirados")
        print("  ✅ SOLUCIÓN: Renovar tokens en Railway")
    elif total_pendientes == 0:
        print("  📝 NO HAY CONTENIDO PARA PUBLICAR")
        print("  ✅ El job está bien, solo no hay nada que hacer")
    else:
        print("  ⚙️ CONFIGURACIÓN INCOMPLETA")
        print("  📋 Revisar páginas y locaciones")

if __name__ == "__main__":
    main()