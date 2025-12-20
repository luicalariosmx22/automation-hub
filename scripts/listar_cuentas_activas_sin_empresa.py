"""
Script para listar las cuentas que están activo=True pero no tienen nombre_empresa
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def main():
    supabase = create_client_from_env()
    
    # Obtener cuentas activas sin nombre_empresa
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_nora,nombre_empresa,empresa_id,cliente_id') \
        .eq('activo', True) \
        .execute()
    
    cuentas_sin_empresa = []
    for cuenta in response.data or []:
        nombre_empresa = cuenta.get('nombre_empresa')
        if not nombre_empresa or nombre_empresa.strip() == '' or nombre_empresa == 'None':
            cuentas_sin_empresa.append(cuenta)
    
    print(f"\n{'='*100}")
    print(f"CUENTAS ACTIVO=TRUE SIN nombre_empresa ({len(cuentas_sin_empresa)})")
    print(f"{'='*100}\n")
    print(f"Estas cuentas aparecen como 'aura' en los reportes\n")
    
    for i, cuenta in enumerate(cuentas_sin_empresa, 1):
        print(f"{i}. ID Cuenta: {cuenta['id_cuenta_publicitaria']}")
        print(f"   nombre_nora: {cuenta.get('nombre_nora')}")
        print(f"   nombre_empresa: {cuenta.get('nombre_empresa')} ← VACÍO")
        print(f"   empresa_id: {cuenta.get('empresa_id')}")
        print(f"   cliente_id: {cuenta.get('cliente_id')}")
        print()
    
    print(f"\n{'='*100}")
    print(f"RECOMENDACIÓN:")
    print(f"{'='*100}")
    print(f"Para estas {len(cuentas_sin_empresa)} cuentas debes:")
    print(f"  1. Si son ex-clientes: poner activo=FALSE")
    print(f"  2. Si son clientes actuales: llenar el campo nombre_empresa")
    print(f"\nQuery para desactivarlas todas:")
    print(f"UPDATE meta_ads_cuentas SET activo = FALSE")
    print(f"WHERE nombre_empresa IS NULL OR nombre_empresa = 'None' OR nombre_empresa = '';")

if __name__ == "__main__":
    main()
