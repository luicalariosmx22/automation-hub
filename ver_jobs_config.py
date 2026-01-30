"""
Script para ver todos los jobs configurados en Supabase.
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def main():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Consultar todos los jobs
    response = supabase.table("jobs_config").select("*").order("job_name").execute()
    
    jobs = response.data
    
    print(f"\n{'='*80}")
    print(f"JOBS CONFIGURADOS EN SUPABASE ({len(jobs)} total)")
    print(f"{'='*80}\n")
    
    for job in jobs:
        enabled = "✓ ACTIVO" if job.get("enabled") else "✗ DESACTIVADO"
        interval = job.get("schedule_interval_minutes", "N/A")
        last_run = job.get("last_run_at", "Nunca")
        next_run = job.get("next_run_at", "N/A")
        
        print(f"Job: {job['job_name']}")
        print(f"  Estado: {enabled}")
        print(f"  Intervalo: cada {interval} minutos")
        print(f"  Última ejecución: {last_run}")
        print(f"  Próxima ejecución: {next_run}")
        print()
    
    # Contar activos vs desactivados
    activos = sum(1 for j in jobs if j.get("enabled"))
    desactivados = len(jobs) - activos
    
    print(f"{'='*80}")
    print(f"RESUMEN: {activos} activos, {desactivados} desactivados")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
