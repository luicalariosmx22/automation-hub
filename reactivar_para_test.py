#!/usr/bin/env python3
"""
Script para reactivar la ubicación específica del test
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def reactivar_ubicacion_test():
    """Reactiva la ubicación para el test específico"""
    supabase = create_client_from_env()
    
    location_name = "locations/564637435873288989"
    empresa_id = "dec4ceff-c826-4b7d-8248-7c5808b59305"
    
    print(f"🔄 Reactivando ubicación: {location_name}")
    print(f"🏢 Para empresa: {empresa_id}")
    
    # Reactivar la ubicación
    result = supabase.table("gbp_locations").update({
        "activa": True
    }).eq("location_name", location_name).eq("empresa_id", empresa_id).execute()
    
    if result.data:
        print("✅ Ubicación reactivada exitosamente")
        print("🧪 Ahora puedes ejecutar: cmd /c \".venv\\Scripts\\activate.bat && python test_post_especifico.py\"")
    else:
        print("❌ No se pudo reactivar la ubicación")
        
if __name__ == "__main__":
    reactivar_ubicacion_test()