"""
Script para verificar los datos de una cuenta específica
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
    
    # Buscar la cuenta
    cuenta_id = '7288454764560251'  # ID correcto
    
    response = supabase.table('meta_ads_cuentas') \
        .select('*') \
        .eq('id_cuenta_publicitaria', cuenta_id) \
        .execute()
    
    if not response.data:
        print(f"❌ No se encontró cuenta con ID: {cuenta_id}")
        return
    
    cuenta = response.data[0]
    
    print(f"\n{'='*100}")
    print(f"DATOS DE LA CUENTA: {cuenta_id}")
    print(f"{'='*100}\n")
    
    print(f"ID Cuenta Publicitaria: {cuenta.get('id_cuenta_publicitaria')}")
    print(f"nombre_cuenta: '{cuenta.get('nombre_cuenta')}'")
    print(f"nombre_nora: '{cuenta.get('nombre_nora')}'")
    print(f"nombre_empresa: '{cuenta.get('nombre_empresa')}'")
    print(f"empresa_id: {cuenta.get('empresa_id')}")
    print(f"cliente_id: {cuenta.get('cliente_id')}")
    print(f"activo: {cuenta.get('activo')}")
    print(f"estado_actual: '{cuenta.get('estado_actual')}'")
    print(f"conectada: {cuenta.get('conectada')}")
    
    # Si tiene empresa_id, buscar el nombre de la empresa
    empresa_id = cuenta.get('empresa_id')
    if empresa_id:
        print(f"\n{'='*100}")
        print(f"BUSCANDO EMPRESA CON ID: {empresa_id}")
        print(f"{'='*100}\n")
        
        empresa_resp = supabase.table('cliente_empresas') \
            .select('*') \
            .eq('id', empresa_id) \
            .execute()
        
        if empresa_resp.data:
            empresa = empresa_resp.data[0]
            print(f"✅ Empresa encontrada:")
            print(f"   ID: {empresa.get('id')}")
            print(f"   Nombre: '{empresa.get('nombre')}'")
            print(f"   Cliente ID: {empresa.get('cliente_id')}")
            
            print(f"\n{'='*100}")
            print(f"SOLUCIÓN:")
            print(f"{'='*100}")
            print(f"Esta cuenta tiene empresa_id pero nombre_empresa está vacío.")
            print(f"Debería actualizarse el campo nombre_empresa con: '{empresa.get('nombre')}'")
            print(f"\nQuery para actualizar:")
            print(f"UPDATE meta_ads_cuentas")
            print(f"SET nombre_empresa = '{empresa.get('nombre')}'")
            print(f"WHERE id_cuenta_publicitaria = '{cuenta_id}';")
        else:
            print(f"❌ No se encontró empresa con ID: {empresa_id}")
    else:
        print(f"\n⚠️  Esta cuenta NO tiene empresa_id asignado")

if __name__ == "__main__":
    main()
