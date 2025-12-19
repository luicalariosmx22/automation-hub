"""Debug: Ver todas las citas de hoy 19/12/2025"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from datetime import datetime, timezone
from automation_hub.db.supabase_client import create_client_from_env
import pytz

supabase = create_client_from_env()

print("🔍 Buscando todas las citas del 19 de diciembre de 2025\n")

# Buscar citas del 19/12/2025 sin importar la hora
result = supabase.table('agenda_citas') \
    .select('id, titulo, inicio, fin, estado, origen') \
    .eq('nombre_nora', 'aura') \
    .gte('inicio', '2025-12-19T00:00:00') \
    .lt('inicio', '2025-12-20T00:00:00') \
    .order('inicio') \
    .execute()

print(f"Total citas encontradas: {len(result.data)}\n")

tz_mx = pytz.timezone('America/Mexico_City')

for i, cita in enumerate(result.data, 1):
    inicio_utc = datetime.fromisoformat(cita['inicio'].replace('Z', '+00:00'))
    inicio_mx = inicio_utc.astimezone(tz_mx)
    
    print(f"{i}. {cita['titulo']}")
    print(f"   Estado: {cita['estado']}")
    print(f"   Origen: {cita.get('origen', 'N/A')}")
    print(f"   UTC: {inicio_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   México: {inicio_mx.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()

print("="*60)
print("💡 El problema es el timezone:")
print("   El job busca en rango UTC 00:00 - 23:59")
print("   Pero las citas pueden estar en hora de México")
print("   que corresponde a diferentes horas UTC")
