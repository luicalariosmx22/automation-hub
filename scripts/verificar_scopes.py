"""Verificar scopes actuales y calendario anterior"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

print("🔍 Verificando configuración OAuth:\n")

result = supabase.table('google_calendar_sync') \
    .select('*') \
    .eq('nombre_nora', 'aura') \
    .execute()

if result.data and len(result.data) > 0:
    data = result.data[0]
    
    print(f"Calendario seleccionado: {data.get('google_calendar_id')}")
    print(f"Calendar ID (alt): {data.get('calendar_id')}")
    print(f"\nScopes actuales:")
    scope = data.get('scope', '')
    for s in scope.split():
        print(f"  - {s}")
    
    print(f"\nToken expires: {data.get('expires_at')}")
    print(f"Token type: {data.get('token_type')}")
    
    # Buscar citas antiguas para ver si antes tenían título
    print("\n" + "="*80)
    print("📋 Citas más antiguas sincronizadas (para ver si tenían título):")
    print("="*80)
    
    citas = supabase.table('agenda_citas') \
        .select('titulo, inicio, google_event_id, origen, creado_en') \
        .eq('nombre_nora', 'aura') \
        .eq('origen', 'google_calendar') \
        .order('creado_en', desc=False) \
        .limit(10) \
        .execute()
    
    for cita in citas.data:
        print(f"\nTítulo: '{cita['titulo']}'")
        print(f"Creado: {cita['creado_en']}")
        print(f"Event ID: {cita['google_event_id']}")
