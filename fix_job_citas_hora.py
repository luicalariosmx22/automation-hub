"""Fix temporal: Programar job de citas para mañana a las 9 AM Hermosillo"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timedelta
import pytz

supabase = create_client_from_env()

# Calcular próximo 9 AM en Hermosillo
hermosillo_tz = pytz.timezone('America/Hermosillo')
ahora_hermosillo = datetime.now(hermosillo_tz)

# Si ya pasaron las 9 AM hoy, programar para mañana
if ahora_hermosillo.hour >= 9:
    proximo_9am = (ahora_hermosillo + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
else:
    proximo_9am = ahora_hermosillo.replace(hour=9, minute=0, second=0, microsecond=0)

# Convertir a UTC
proximo_9am_utc = proximo_9am.astimezone(pytz.UTC)

print(f"⏰ Programando job de citas para: {proximo_9am.strftime('%Y-%m-%d %H:%M')} (Hermosillo)")
print(f"   En UTC: {proximo_9am_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")

# Actualizar en la BD
result = supabase.table('jobs_config').update({
    'next_run_at': proximo_9am_utc.isoformat()
}).eq('job_name', 'calendar.daily.summary').execute()

if result.data:
    print("✅ Job actualizado correctamente")
    print(f"   Próxima ejecución: {result.data[0]['next_run_at']}")
else:
    print("❌ Error actualizando job")
