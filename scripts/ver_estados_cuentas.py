"""
Script para ver los diferentes valores de estado_actual en meta_ads_cuentas
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
    
    # Obtener todas las cuentas con activo=True
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_empresa,nombre_nora,estado_actual,activo,empresa_id') \
        .eq('activo', True) \
        .execute()
    
    cuentas = response.data or []
    
    # Agrupar por estado_actual
    por_estado = {}
    for cuenta in cuentas:
        estado = cuenta.get('estado_actual') or 'NULL'
        if estado not in por_estado:
            por_estado[estado] = []
        por_estado[estado].append(cuenta)
    
    print(f"\n{'='*100}")
    print(f"ESTADOS DE CUENTAS (activo=True)")
    print(f"{'='*100}\n")
    
    for estado, cuentas_estado in sorted(por_estado.items()):
        print(f"\n📊 estado_actual = '{estado}' ({len(cuentas_estado)} cuentas)")
        print(f"{'-'*100}")
        
        for cuenta in cuentas_estado[:5]:
            nombre_empresa = cuenta.get('nombre_empresa') or 'SIN EMPRESA'
            nombre_nora = cuenta.get('nombre_nora')
            empresa_id = cuenta.get('empresa_id') or 'NULL'
            
            print(f"  • {nombre_empresa} ({nombre_nora})")
            print(f"    ID: {cuenta['id_cuenta_publicitaria']}, empresa_id: {empresa_id}")
        
        if len(cuentas_estado) > 5:
            print(f"  ... y {len(cuentas_estado) - 5} más")
    
    print(f"\n{'='*100}")
    print(f"RESUMEN POR ESTADO:")
    print(f"{'='*100}")
    for estado, cuentas_estado in sorted(por_estado.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {estado:15} : {len(cuentas_estado):3} cuentas")
    
    print(f"\n{'='*100}")
    print(f"TOTAL CUENTAS activo=True: {len(cuentas)}")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()
