"""Ver estructura de la tabla google_calendar_sync"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

print("📊 Consultando tabla google_calendar_sync\n")

result = supabase.table('google_calendar_sync') \
    .select('*') \
    .eq('nombre_nora', 'aura') \
    .execute()

if result.data:
    import json
    print("✅ Datos encontrados:")
    print(json.dumps(result.data[0], indent=2, default=str))
    print("\n📋 Columnas disponibles:")
    for key in result.data[0].keys():
        print(f"   - {key}")
else:
    print("❌ No se encontraron datos")
