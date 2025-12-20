"""Script para verificar que el registry funcione correctamente"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from automation_hub.jobs.registry import list_jobs

job_names = list_jobs()
print(f"\n✅ Jobs registrados exitosamente: {len(job_names)}")
print("\nLista de jobs:")
for name in job_names:
    print(f"  - {name}")

print("\n¡Registro funcionando correctamente!")
