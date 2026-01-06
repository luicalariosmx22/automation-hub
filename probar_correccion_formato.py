#!/usr/bin/env python3
"""
Script para probar la corrección de formato de ubicaciones GBP
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import fix_location_format, get_account_id

def probar_correccion_formato():
    """Probar la corrección de formato para todas las ubicaciones"""
    supabase = create_client_from_env()
    
    print("🔧 PROBANDO CORRECCIÓN DE FORMATO DE UBICACIONES")
    print("=" * 60)
    
    # Obtener auth headers
    try:
        auth_headers = get_bearer_header()
        print("✅ Auth headers obtenidos correctamente")
    except Exception as e:
        print(f"❌ Error obteniendo auth headers: {e}")
        return
    
    # Obtener account ID
    try:
        account_id = get_account_id(auth_headers)
        print(f"📋 Account ID: {account_id}")
        print()
    except Exception as e:
        print(f"❌ Error obteniendo account ID: {e}")
        return
    
    # Obtener todas las ubicaciones activas
    ubicaciones = supabase.table("gbp_locations")\
        .select("*")\
        .eq("activa", True)\
        .execute()
    
    print(f"📍 Total ubicaciones activas: {len(ubicaciones.data)}")
    print()
    
    formatos_correctos = 0
    formatos_incorrectos = 0
    
    for ubicacion in ubicaciones.data:
        location_name = ubicacion.get("location_name", "")
        empresa_id = ubicacion.get("empresa_id", "") or ""
        empresa_display = empresa_id[:20] if empresa_id else "Sin empresa"
        
        print(f"🏢 Empresa: {empresa_display}...")
        print(f"📍 Original: {location_name}")
        
        # Probar corrección
        try:
            corregido = fix_location_format(location_name, auth_headers)
            print(f"✅ Corregido: {corregido}")
            
            if corregido != location_name:
                formatos_incorrectos += 1
                print("   🔧 NECESITABA CORRECCIÓN")
            else:
                formatos_correctos += 1
                print("   ✅ YA ESTABA CORRECTO")
                
        except Exception as e:
            print(f"   ❌ Error en corrección: {e}")
        
        print("-" * 40)
    
    print()
    print(f"📊 RESUMEN:")
    print(f"✅ Formatos correctos: {formatos_correctos}")
    print(f"🔧 Necesitaban corrección: {formatos_incorrectos}")

if __name__ == "__main__":
    probar_correccion_formato()