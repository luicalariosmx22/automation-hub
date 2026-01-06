#!/usr/bin/env python3
"""
Script para actualizar los formatos de ubicaciones en la base de datos
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import fix_location_format, get_account_id

def actualizar_formatos_ubicaciones():
    """Actualizar formatos de ubicaciones en la base de datos"""
    supabase = create_client_from_env()
    
    print("🔧 ACTUALIZANDO FORMATOS DE UBICACIONES EN BASE DE DATOS")
    print("=" * 60)
    
    # Obtener auth headers
    try:
        auth_headers = get_bearer_header()
        account_id = get_account_id(auth_headers)
        print(f"✅ Account ID: {account_id}")
        print()
    except Exception as e:
        print(f"❌ Error obteniendo auth: {e}")
        return
    
    # Obtener todas las ubicaciones activas con formato incorrecto
    ubicaciones = supabase.table("gbp_locations")\
        .select("*")\
        .eq("activa", True)\
        .not_.like("location_name", "accounts/%")\
        .execute()
    
    print(f"📍 Ubicaciones que necesitan actualización: {len(ubicaciones.data)}")
    print()
    
    actualizaciones_exitosas = 0
    errores = 0
    
    for ubicacion in ubicaciones.data:
        location_id = ubicacion.get("id")
        location_name = ubicacion.get("location_name", "")
        empresa_id = ubicacion.get("empresa_id", "") or ""
        empresa_display = empresa_id[:20] if empresa_id else "Sin empresa"
        
        print(f"🏢 {empresa_display}...")
        print(f"📍 Actual: {location_name}")
        
        try:
            # Corregir formato
            nuevo_formato = fix_location_format(location_name, auth_headers)
            print(f"✅ Nuevo: {nuevo_formato}")
            
            # Actualizar en base de datos
            resultado = supabase.table("gbp_locations")\
                .update({"location_name": nuevo_formato})\
                .eq("id", location_id)\
                .execute()
            
            if resultado.data:
                print("   ✅ ACTUALIZADO EN BD")
                actualizaciones_exitosas += 1
            else:
                print("   ❌ Error actualizando en BD")
                errores += 1
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            errores += 1
        
        print("-" * 40)
    
    print()
    print(f"📊 RESUMEN:")
    print(f"✅ Actualizaciones exitosas: {actualizaciones_exitosas}")
    print(f"❌ Errores: {errores}")
    
    if actualizaciones_exitosas > 0:
        print()
        print("🔄 AHORA NECESITAS RE-PROCESAR LAS PUBLICACIONES QUE FALLARON")
        print("   Puedes resetear publicada_gbp = false para las que necesiten reintento")

if __name__ == "__main__":
    actualizar_formatos_ubicaciones()