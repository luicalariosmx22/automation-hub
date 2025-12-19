"""Configurar intervalos de tiempo para cada job"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timezone

print("⏰ Configurando intervalos de ejecución...\n")

sb = create_client_from_env()

# Configuración de intervalos
configuracion = {
    'gbp.reviews.daily': {
        'interval': 60,  # Cada 60 minutos (1 hora)
        'descripcion': 'Reseñas de Google Business Profile'
    },
    'meta_ads.cuentas.sync.daily': {
        'interval': 60,  # Cada 60 minutos (1 hora)
        'descripcion': 'Detectar cuentas Meta Ads desactivadas'
    },
    'meta_ads.rechazos.daily': {
        'interval': 10,  # Cada 10 minutos
        'descripcion': 'Detectar anuncios rechazados en Meta Ads'
    },
    'gbp.metrics.daily': {
        'interval': 1440,  # Cada 24 horas (diario)
        'descripcion': 'Métricas diarias de Google Business Profile'
    }
}

print("📋 Configuración a aplicar:\n")
for job_name, config in configuracion.items():
    interval = config['interval']
    if interval < 60:
        tiempo = f"{interval} minutos"
    elif interval == 60:
        tiempo = "1 hora"
    elif interval == 1440:
        tiempo = "24 horas (diario)"
    else:
        tiempo = f"{interval} minutos ({interval/60:.1f} horas)"
    
    print(f"🔧 {job_name}")
    print(f"   Intervalo: {tiempo}")
    print(f"   Descripción: {config['descripcion']}")
    print()

respuesta = input("¿Aplicar esta configuración? (s/n): ").strip().lower()

if respuesta == 's':
    print("\n🔄 Aplicando cambios...\n")
    
    for job_name, config in configuracion.items():
        # Actualizar intervalo y programar próxima ejecución para AHORA
        update_data = {
            'schedule_interval_minutes': config['interval'],
            'next_run_at': datetime.now(timezone.utc).isoformat()
        }
        
        result = sb.table('jobs_config').update(update_data).eq('job_name', job_name).execute()
        
        if result.data:
            print(f"✅ {job_name} actualizado")
        else:
            # Si no existe, crear el job
            insert_data = {
                'job_name': job_name,
                'enabled': True,
                'schedule_interval_minutes': config['interval'],
                'next_run_at': datetime.now(timezone.utc).isoformat(),
                'config': {'descripcion': config['descripcion']}
            }
            result = sb.table('jobs_config').insert(insert_data).execute()
            if result.data:
                print(f"➕ {job_name} creado")
            else:
                print(f"❌ Error con {job_name}")
    
    print("\n" + "="*60)
    print("✅ Configuración aplicada exitosamente!")
    print("\n📊 Resumen:")
    print("   • Reseñas GBP → cada 1 hora")
    print("   • Cuentas Meta Ads → cada 1 hora")
    print("   • Anuncios rechazados → cada 10 minutos ⚡")
    print("   • Métricas GBP → cada 24 horas")
    print("\n🚀 Los jobs se ejecutarán en la próxima corrida del batch runner")
else:
    print("\n❌ Operación cancelada")
