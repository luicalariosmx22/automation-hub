"""
Script para ver qué cuentas tienen nombre_empresa vacío/NULL
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def main():
    supabase = create_client_from_env()
    
    # Obtener todas las cuentas activas
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_cuenta,nombre_nora,nombre_empresa,empresa_id') \
        .eq('activo', True) \
        .execute()
    
    cuentas = response.data or []
    
    # Separar por si tienen o no nombre_empresa
    con_empresa = []
    sin_empresa = []
    
    for cuenta in cuentas:
        nombre_empresa = cuenta.get('nombre_empresa')
        if nombre_empresa and nombre_empresa.strip():
            con_empresa.append(cuenta)
        else:
            sin_empresa.append(cuenta)
    
    print(f"\n{'='*80}")
    print(f"CUENTAS CON nombre_empresa ({len(con_empresa)})")
    print(f"{'='*80}\n")
    
    for cuenta in con_empresa[:10]:
        print(f"  • {cuenta.get('nombre_empresa')} (ID: {cuenta.get('id_cuenta_publicitaria')})")
    
    if len(con_empresa) > 10:
        print(f"  ... y {len(con_empresa) - 10} más\n")
    
    print(f"\n{'='*80}")
    print(f"CUENTAS SIN nombre_empresa - usan fallback ({len(sin_empresa)})")
    print(f"{'='*80}\n")
    
    for cuenta in sin_empresa:
        id_cuenta = cuenta.get('id_cuenta_publicitaria')
        nombre_nora = cuenta.get('nombre_nora', '')
        nombre_cuenta = cuenta.get('nombre_cuenta', '')
        nombre_empresa = cuenta.get('nombre_empresa', '')
        empresa_id = cuenta.get('empresa_id', '')
        
        # Este es el nombre que se mostraría en el reporte
        nombre_mostrado = nombre_nora or nombre_cuenta or 'Sin nombre'
        
        print(f"  📍 {nombre_mostrado}")
        print(f"     ID Cuenta: {id_cuenta}")
        print(f"     nombre_empresa: '{nombre_empresa}' (vacío)")
        print(f"     empresa_id: {empresa_id}")
        print(f"     nombre_nora: '{nombre_nora}'")
        print(f"     nombre_cuenta: '{nombre_cuenta}'")
        print()
    
    print(f"\nRESUMEN:")
    print(f"  ✅ Con nombre_empresa: {len(con_empresa)}")
    print(f"  ⚠️  Sin nombre_empresa (usan fallback): {len(sin_empresa)}")
    print(f"  📊 Total cuentas activas: {len(cuentas)}")

if __name__ == "__main__":
    main()
