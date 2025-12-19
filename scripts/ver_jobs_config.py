"""Ver configuración de jobs en Supabase"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timezone

sb = create_client_from_env()

print("📋 Configuración de Jobs en Supabase:\n")

result = sb.table('jobs_config').select('*').order('job_name').execute()

if not result.data:
    print("❌ No hay jobs configurados en la tabla jobs_config")
    print("\n💡 Necesitas:")
    print("   1. Correr la migración: db/migrations/001_jobs_config.sql")
    print("   2. Insertar los jobs en la tabla")
else:
    print(f"Total jobs: {len(result.data)}\n")
    
    ahora = datetime.now(timezone.utc)
    
    for job in result.data:
        nombre = job.get('job_name')
        enabled = job.get('enabled')
        interval = job.get('schedule_interval_minutes')
        next_run = job.get('next_run_at')
        last_run = job.get('last_run_at')
        
        estado = "✅ ACTIVO" if enabled else "❌ DESHABILITADO"
        
        print(f"🔧 {nombre}")
        print(f"   Estado: {estado}")
        print(f"   Intervalo: cada {interval} minutos")
        print(f"   Última ejecución: {last_run or 'Nunca'}")
        print(f"   Próxima ejecución: {next_run or 'No programada'}")
        
        if enabled and next_run:
            next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
            if next_run_dt <= ahora:
                print(f"   ⏰ LISTO PARA EJECUTAR")
            else:
                diff = (next_run_dt - ahora).total_seconds() / 60
                print(f"   ⏳ Falta {diff:.1f} minutos")
        
        print()

print("\n" + "="*60)
print("Para que los jobs se ejecuten:")
print("  1. enabled = true")
print("  2. next_run_at <= AHORA (o NULL para ejecutar inmediatamente)")
