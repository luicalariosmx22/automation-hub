"""
Verifica el schema de logs_webhooks_meta
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

print("\n" + "="*80)
print("📊 SCHEMA: logs_webhooks_meta")
print("="*80 + "\n")

# Obtener un registro para ver las columnas
result = supabase.table('logs_webhooks_meta').select('*').limit(1).execute()

if result.data:
    print("Columnas disponibles:")
    for col in sorted(result.data[0].keys()):
        valor = result.data[0][col]
        tipo = type(valor).__name__
        print(f"  • {col:30} ({tipo})")
    
    print("\n" + "="*80)
    print("Ejemplo de registro:")
    print("="*80)
    import json
    print(json.dumps(result.data[0], indent=2, default=str)[:500])
else:
    print("⚠️ No hay registros en logs_webhooks_meta")

# Contar pendientes
print("\n" + "="*80)
print("📊 WEBHOOKS PENDIENTES:")
print("="*80 + "\n")

try:
    pendientes = supabase.table('logs_webhooks_meta') \
        .select('id, tipo_objeto', count='exact') \
        .eq('procesado', False) \
        .execute()
    
    print(f"Total pendientes: {pendientes.count}")
    
    if pendientes.data:
        # Agrupar por tipo
        tipos = {}
        for item in pendientes.data:
            tipo = item.get('tipo_objeto', 'unknown')
            tipos[tipo] = tipos.get(tipo, 0) + 1
        
        print("\nPor tipo de objeto:")
        for tipo, count in tipos.items():
            print(f"  • {tipo}: {count}")
except Exception as e:
    print(f"Error: {e}")

print()
