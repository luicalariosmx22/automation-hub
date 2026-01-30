"""Ejecutar migración para agregar schedule_time a jobs_config"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from automation_hub.db.supabase_client import create_client_from_env
from pathlib import Path

supabase = create_client_from_env()

# Leer SQL de migración
sql_file = Path("migrations/add_schedule_time_to_jobs.sql")
with open(sql_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

print("📄 Ejecutando migración: add_schedule_time_to_jobs.sql\n")

# Dividir en statements individuales (PostgreSQL permite ejecutar múltiples)
# pero es más seguro ejecutar uno por uno para ver errores específicos
statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

for i, statement in enumerate(statements, 1):
    if not statement:
        continue
    
    # Mostrar primeras líneas del statement
    preview = statement.split('\n')[0][:80]
    print(f"{i}. Ejecutando: {preview}...")
    
    try:
        # Usar RPC para ejecutar SQL directo
        result = supabase.rpc('exec_sql', {'query': statement}).execute()
        print(f"   ✅ Éxito")
    except Exception as e:
        error_msg = str(e)
        # Si es "function exec_sql does not exist", usar otro método
        if "does not exist" in error_msg or "exec_sql" in error_msg:
            print(f"   ℹ️  RPC no disponible, usa SQL Editor en Supabase")
            print("\n" + "="*80)
            print("⚠️  No se puede ejecutar SQL directamente desde Python")
            print("Por favor, ejecuta este SQL en Supabase SQL Editor:")
            print("="*80)
            print(sql_content)
            print("="*80)
            break
        else:
            print(f"   ❌ Error: {error_msg}")
            break

print("\n✅ Migración completada")
print("\nVerificando cambios...")

# Verificar que la columna se creó
try:
    result = supabase.table('jobs_config').select('job_name, schedule_time, next_run_at').eq('job_name', 'calendar.daily.summary').execute()
    if result.data:
        job = result.data[0]
        print(f"\n📋 Job calendar.daily.summary:")
        print(f"  • schedule_time: {job.get('schedule_time')}")
        print(f"  • next_run_at: {job.get('next_run_at')}")
    else:
        print("❌ Job calendar.daily.summary no encontrado")
except Exception as e:
    print(f"⚠️  Error verificando: {e}")
