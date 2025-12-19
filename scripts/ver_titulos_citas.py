"""Ver títulos de las citas de hoy en BD"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

print("📋 Citas de hoy (19 dic) en BD:\n")

result = supabase.table('agenda_citas') \
    .select('titulo, inicio, google_event_id, origen') \
    .eq('nombre_nora', 'aura') \
    .gte('inicio', '2025-12-19T07:00:00+00:00') \
    .lte('inicio', '2025-12-20T06:59:59+00:00') \
    .neq('estado', 'cancelada') \
    .order('inicio') \
    .execute()

for i, cita in enumerate(result.data, 1):
    print(f"{i}. Título: '{cita['titulo']}'")
    print(f"   Inicio: {cita['inicio']}")
    print(f"   Event ID: {cita['google_event_id']}")
    print(f"   Origen: {cita.get('origen', 'N/A')}")
    print()
