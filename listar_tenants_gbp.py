"""
Script para listar los tenants (nombre_nora) disponibles en la base de datos.
"""
import os
import sys
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

# Cargar variables de entorno
load_dotenv()

# Conectar a Supabase
supabase = create_client_from_env()

# Consultar ubicaciones
print("\n" + "="*60)
print("UBICACIONES GBP EN LA BASE DE DATOS")
print("="*60 + "\n")

result = supabase.table("gbp_locations").select("nombre_nora, title, location_id, activa").execute()

if result.data:
    # Agrupar por nombre_nora
    tenants = {}
    for loc in result.data:
        nombre_nora = loc.get("nombre_nora", "N/A")
        if nombre_nora not in tenants:
            tenants[nombre_nora] = []
        tenants[nombre_nora].append(loc)
    
    print(f"Total de ubicaciones: {len(result.data)}")
    print(f"Total de tenants: {len(tenants)}\n")
    
    for tenant, ubicaciones in sorted(tenants.items()):
        activas = sum(1 for u in ubicaciones if u.get("activa", False))
        print(f"📍 {tenant}")
        print(f"   Total: {len(ubicaciones)} ubicaciones")
        print(f"   Activas: {activas}")
        
        # Mostrar primeras 3 ubicaciones
        for i, ub in enumerate(ubicaciones[:3]):
            print(f"   - {ub.get('title', 'Sin título')} ({ub.get('location_id', 'N/A')})")
        
        if len(ubicaciones) > 3:
            print(f"   ... y {len(ubicaciones) - 3} más")
        print()
else:
    print("❌ No se encontraron ubicaciones en la base de datos")
