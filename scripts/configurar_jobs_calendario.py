"""
Script para configurar los jobs de calendario en la base de datos.
- calendar.sync: Cada 30 minutos
- calendar.daily.summary: Diario a las 9:00 AM
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from datetime import datetime, time, timedelta
import pytz
from automation_hub.db.supabase_client import create_client_from_env

def configurar_jobs_calendario():
    """Configura los jobs de calendario en la base de datos."""
    supabase = create_client_from_env()
    
    # Timezone de México
    tz = pytz.timezone('America/Mexico_City')
    ahora = datetime.now(tz)
    
    # Configurar calendar.sync (cada 30 minutos)
    print("Configurando job: calendar.sync")
    
    # Verificar si ya existe
    result = supabase.table('jobs_config').select('*').eq('job_name', 'calendar.sync').execute()
    
    if result.data:
        print("  ✓ Job calendar.sync ya existe, actualizando...")
        supabase.table('jobs_config').update({
            'enabled': True,
            'schedule_interval_minutes': 30,
            'next_run_at': ahora.isoformat(),
            'updated_at': ahora.isoformat()
        }).eq('job_name', 'calendar.sync').execute()
    else:
        print("  ✓ Creando job calendar.sync...")
        supabase.table('jobs_config').insert({
            'job_name': 'calendar.sync',
            'enabled': True,
            'schedule_interval_minutes': 30,
            'next_run_at': ahora.isoformat(),
            'created_at': ahora.isoformat(),
            'updated_at': ahora.isoformat()
        }).execute()
    
    print("  ✓ calendar.sync configurado: cada 30 minutos")
    
    # Configurar calendar.daily.summary (diario a las 9 AM)
    print("\nConfigurando job: calendar.daily.summary")
    
    # Calcular próxima ejecución a las 9:00 AM
    hoy_9am = tz.localize(datetime.combine(ahora.date(), time(9, 0)))
    
    if ahora >= hoy_9am:
        # Si ya pasaron las 9 AM, programar para mañana
        proxima_ejecucion = hoy_9am + timedelta(days=1)
    else:
        # Si no han pasado las 9 AM, programar para hoy
        proxima_ejecucion = hoy_9am
    
    # Verificar si ya existe
    result = supabase.table('jobs_config').select('*').eq('job_name', 'calendar.daily.summary').execute()
    
    if result.data:
        print("  ✓ Job calendar.daily.summary ya existe, actualizando...")
        supabase.table('jobs_config').update({
            'enabled': True,
            'schedule_interval_minutes': 1440,  # 24 horas
            'next_run_at': proxima_ejecucion.isoformat(),
            'updated_at': ahora.isoformat()
        }).eq('job_name', 'calendar.daily.summary').execute()
    else:
        print("  ✓ Creando job calendar.daily.summary...")
        supabase.table('jobs_config').insert({
            'job_name': 'calendar.daily.summary',
            'enabled': True,
            'schedule_interval_minutes': 1440,  # 24 horas
            'next_run_at': proxima_ejecucion.isoformat(),
            'created_at': ahora.isoformat(),
            'updated_at': ahora.isoformat()
        }).execute()
    
    print(f"  ✓ calendar.daily.summary configurado: diario a las 9:00 AM")
    print(f"  ✓ Próxima ejecución: {proxima_ejecucion.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    print("\n✅ Configuración de jobs de calendario completada")
    print("\n📋 Resumen:")
    print("   - calendar.sync: Sincroniza eventos de Google Calendar cada 30 minutos")
    print("   - calendar.daily.summary: Envía resumen diario a las 9:00 AM a todo el equipo")
    print("\n⚠️  Nota: Asegúrate de que las credenciales OAuth de Google Calendar estén configuradas")
    print("   en las variables de entorno: GOOGLE_OAUTH_CLIENT_ID y GOOGLE_OAUTH_CLIENT_SECRET")

if __name__ == '__main__':
    try:
        configurar_jobs_calendario()
    except Exception as e:
        print(f"❌ Error al configurar jobs: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
