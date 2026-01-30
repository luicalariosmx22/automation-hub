"""Ejecutar job de citas manualmente para verificar sincronización de Google Calendar"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print("=" * 80)
print("🔄 EJECUTANDO JOB: calendar.daily.summary")
print("=" * 80)
print()

from automation_hub.jobs import calendar_daily_summary

try:
    calendar_daily_summary.run()
    print("\n✅ Job completado exitosamente")
except Exception as e:
    print(f"\n❌ Error en job: {e}")
    import traceback
    traceback.print_exc()
