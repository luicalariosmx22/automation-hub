"""
Script para agregar el job gbp.locations.sync a jobs_config
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime

supabase = create_client_from_env()

# Insertar o actualizar el job
job_data = {
    "job_name": "gbp.locations.sync",
    "enabled": True,
    "interval_minutes": 1440,  # 24 horas
    "next_run_at": datetime.utcnow().isoformat(),
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat()
}

# Verificar si existe
existing = supabase.table("jobs_config").select("job_name").eq("job_name", "gbp.locations.sync").execute()

if existing.data:
    # Actualizar
    supabase.table("jobs_config").update({
        "enabled": True,
        "interval_minutes": 1440,
        "next_run_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }).eq("job_name", "gbp.locations.sync").execute()
    print("✅ Job gbp.locations.sync actualizado en jobs_config")
else:
    # Insertar
    supabase.table("jobs_config").insert(job_data).execute()
    print("✅ Job gbp.locations.sync agregado a jobs_config")

print("\n📋 Configuración:")
print(f"  - Nombre: gbp.locations.sync")
print(f"  - Intervalo: 1440 minutos (24 horas)")
print(f"  - Estado: Habilitado")
print(f"  - Próxima ejecución: Inmediata")
