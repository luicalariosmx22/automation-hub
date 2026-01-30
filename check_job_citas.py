"""Verificar configuración del job de citas"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from automation_hub.db.supabase_client import create_client_from_env
import json

supabase = create_client_from_env()

# Buscar job de citas
result = supabase.table('jobs_config').select('*').eq('job_name', 'calendar.daily.summary').execute()

if result.data:
    print("📋 Configuración del job calendar.daily.summary:\n")
    job = result.data[0]
    print(f"  • Habilitado: {job.get('enabled')}")
    print(f"  • Intervalo (minutos): {job.get('schedule_interval_minutes')}")
    print(f"  • Última ejecución: {job.get('last_run_at')}")
    print(f"  • Próxima ejecución: {job.get('next_run_at')}")
    print(f"  • Config: {json.dumps(job.get('config'), indent=4)}")
else:
    print("❌ Job 'calendar.daily.summary' NO encontrado en jobs_config")
    print("\nBuscando todos los jobs que contienen 'calendar'...")
    result_all = supabase.table('jobs_config').select('job_name').like('job_name', '%calendar%').execute()
    if result_all.data:
        print("Jobs encontrados:")
        for j in result_all.data:
            print(f"  - {j['job_name']}")
    else:
        print("Ningún job relacionado con calendar encontrado")
