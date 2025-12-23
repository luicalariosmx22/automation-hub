import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timedelta

client = create_client_from_env()

print("\n=== AJUSTANDO meta_ads.anuncios.daily ===\n")

# 7:00 AM México = 14:00 UTC
now_utc = datetime.utcnow()
next_run = now_utc.replace(hour=14, minute=0, second=0, microsecond=0)

# Si ya pasaron las 14:00 UTC, programar para mañana
if now_utc.hour >= 14:
    next_run += timedelta(days=1)

print(f"Próxima ejecución:")
print(f"  UTC: {next_run.strftime('%Y-%m-%d %H:%M')}")
print(f"  México: {(next_run - timedelta(hours=7)).strftime('%Y-%m-%d %H:%M')}")

# Actualizar
result = client.table('jobs_config').update({
    'next_run_at': next_run.isoformat() + '+00:00'
}).eq('job_name', 'meta_ads.anuncios.daily').execute()

if result.data:
    print(f"\n✅ Job actualizado - Se ejecutará a las 7:00 AM hora de México")
else:
    print(f"\n❌ Error actualizando job")
