"""
Script para rellenar nombre_empresa en meta_ads_cuentas
usando los datos de la tabla cliente_empresas
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
    
    # 1. Obtener cuentas con empresa_id pero sin nombre_empresa
    print("\n" + "="*100)
    print("BUSCANDO CUENTAS CON EMPRESA_ID PERO SIN NOMBRE_EMPRESA")
    print("="*100 + "\n")
    
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_empresa,empresa_id,cliente_empresas(nombre)') \
        .not_.is_('empresa_id', 'null') \
        .execute()
    
    cuentas = response.data or []
    print(f"Total cuentas con empresa_id: {len(cuentas)}")
    
    # Filtrar las que tienen nombre_empresa vacío o 'None'
    cuentas_sin_nombre = []
    for cuenta in cuentas:
        nombre_empresa = cuenta.get('nombre_empresa')
        if not nombre_empresa or nombre_empresa == 'None' or nombre_empresa.strip() == '':
            cuentas_sin_nombre.append(cuenta)
    
    print(f"Cuentas que necesitan actualización: {len(cuentas_sin_nombre)}\n")
    
    if len(cuentas_sin_nombre) == 0:
        print("✅ Todas las cuentas ya tienen nombre_empresa configurado")
        return
    
    # 2. Actualizar cada cuenta
    actualizadas = 0
    sin_nombre_empresa = 0
    
    for cuenta in cuentas_sin_nombre:
        cuenta_id = cuenta['id_cuenta_publicitaria']
        empresa_data = cuenta.get('cliente_empresas')
        
        if empresa_data and isinstance(empresa_data, dict):
            nombre = empresa_data.get('nombre')
            if nombre and nombre != 'None' and nombre.strip() != '':
                # Actualizar nombre_empresa
                try:
                    supabase.table('meta_ads_cuentas') \
                        .update({'nombre_empresa': nombre}) \
                        .eq('id_cuenta_publicitaria', cuenta_id) \
                        .execute()
                    
                    print(f"✅ Actualizado: {cuenta_id} -> '{nombre}'")
                    actualizadas += 1
                except Exception as e:
                    print(f"❌ Error al actualizar {cuenta_id}: {e}")
            else:
                print(f"⚠️  Sin nombre: {cuenta_id} (empresa sin nombre en BD)")
                sin_nombre_empresa += 1
        else:
            print(f"⚠️  Sin empresa: {cuenta_id} (empresa_id no válido)")
            sin_nombre_empresa += 1
    
    print("\n" + "="*100)
    print("RESUMEN")
    print("="*100)
    print(f"✅ Cuentas actualizadas: {actualizadas}")
    print(f"⚠️  Cuentas sin nombre de empresa en BD: {sin_nombre_empresa}")
    print(f"📊 Total procesadas: {len(cuentas_sin_nombre)}")
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
