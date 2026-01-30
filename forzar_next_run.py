"""
Script para forzar que un job esté listo para ejecutar.
Actualiza next_run_at a NOW() para que el batch runner lo detecte.
"""
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

def main():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    supabase = create_client(supabase_url, supabase_key)
    
    job_name = input("¿Qué job quieres forzar? (ej: meta.to_gbp.daily): ").strip()
    
    if not job_name:
        print("❌ Debes especificar un job")
        return
    
    # Actualizar next_run_at a ahora
    response = supabase.table("jobs_config").update({
        "next_run_at": datetime.utcnow().isoformat()
    }).eq("job_name", job_name).execute()
    
    if response.data:
        print(f"✓ Job '{job_name}' marcado como listo para ejecutar")
        print(f"  Ejecuta: python -m automation_hub.runners.run_batch")
    else:
        print(f"❌ Job '{job_name}' no encontrado")

if __name__ == "__main__":
    main()
