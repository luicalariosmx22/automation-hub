"""Cambiar hora del job de citas a 8 AM Hermosillo (15:00 UTC)"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timedelta
import pytz

supabase = create_client_from_env()

# 8 AM Hermosillo = 15:00 UTC (Hermosillo es UTC-7)
nueva_hora_utc = '15:00:00'

print(f"⏰ Cambiando job de citas a 8:00 AM Hermosillo (15:00 UTC)")

# Calcular próximo 8 AM en Hermosillo
hermosillo_tz = pytz.timezone('America/Hermosillo')
ahora_hermosillo = datetime.now(hermosillo_tz)

# Si ya pasaron las 8 AM hoy, programar para mañana
if ahora_hermosillo.hour >= 8:
    proximo_8am = (ahora_hermosillo + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
else:
    proximo_8am = ahora_hermosillo.replace(hour=8, minute=0, second=0, microsecond=0)

# Convertir a UTC
proximo_8am_utc = proximo_8am.astimezone(pytz.UTC)

print(f"   Próxima ejecución: {proximo_8am.strftime('%Y-%m-%d %H:%M')} (Hermosillo)")
print(f"   En UTC: {proximo_8am_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")

# Actualizar en la BD
result = supabase.table('jobs_config').update({
    'schedule_time': nueva_hora_utc,
    'next_run_at': proximo_8am_utc.isoformat()
}).eq('job_name', 'calendar.daily.summary').execute()

if result.data:
    print("✅ Job actualizado correctamente")
    print(f"\n📋 Nueva configuración:")
    print(f"  • schedule_time: {result.data[0]['schedule_time']}")
    print(f"  • next_run_at: {result.data[0]['next_run_at']}")
else:
    print("❌ Error actualizando job")
