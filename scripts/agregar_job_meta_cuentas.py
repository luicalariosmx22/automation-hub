"""Agregar el job meta_ads.cuentas.sync.daily a la configuración"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timezone

print("➕ Agregando job meta_ads.cuentas.sync.daily...\n")

sb = create_client_from_env()

# Verificar si ya existe
result = sb.table('jobs_config').select('*').eq('job_name', 'meta_ads.cuentas.sync.daily').execute()

if result.data:
    print(f"⚠️ El job ya existe:")
    job = result.data[0]
    print(f"   Estado: {'✅ ACTIVO' if job['enabled'] else '❌ DESHABILITADO'}")
    print(f"   Intervalo: {job['schedule_interval_minutes']} minutos")
    print(f"   Próxima ejecución: {job['next_run_at']}")
else:
    # Insertar el nuevo job
    nuevo_job = {
        'job_name': 'meta_ads.cuentas.sync.daily',
        'enabled': True,
        'schedule_interval_minutes': 1440,  # Diario
        'next_run_at': datetime.now(timezone.utc).isoformat(),  # Ejecutar ahora
        'config': {
            'descripcion': 'Sincroniza estado de cuentas publicitarias y detecta desactivaciones'
        }
    }
    
    result = sb.table('jobs_config').insert(nuevo_job).execute()
    
    if result.data:
        print("✅ Job agregado exitosamente!")
        print(f"\n📋 Configuración:")
        print(f"   Nombre: meta_ads.cuentas.sync.daily")
        print(f"   Estado: ✅ ACTIVO")
        print(f"   Intervalo: 1440 minutos (24 horas)")
        print(f"   Próxima ejecución: AHORA (se ejecutará en el próximo batch)")
        print(f"\n🚨 Este job detecta cuentas Meta Ads desactivadas")
        print(f"   y envía alertas de prioridad ALTA al equipo")
    else:
        print("❌ Error al agregar el job")

print("\n" + "="*60)
print("Ahora tienes 4 jobs configurados:")
print("  1. gbp.reviews.daily")
print("  2. gbp.metrics.daily") 
print("  3. meta_ads.rechazos.daily")
print("  4. meta_ads.cuentas.sync.daily ⭐ NUEVO")
