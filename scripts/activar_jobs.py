"""
Script para activar y configurar los jobs con sus horarios cron.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')

# Agregar src al path
sys.path.insert(0, str(root_dir / 'src'))

from automation_hub.db.supabase_client import create_client_from_env


# Configuración de jobs con sus horarios
JOBS_CONFIG = {
    'gbp.reviews.daily': {
        'enabled': True,
        'schedule_interval_minutes': 1440,  # Diario (24 horas)
        'config': {'description': 'Sincroniza reseñas de Google Business Profile diariamente'}
    },
    'gbp.metrics.daily': {
        'enabled': True,
        'schedule_interval_minutes': 1440,  # Diario
        'config': {'description': 'Sincroniza métricas de Google Business Profile diariamente'}
    },
    'calendar.sync': {
        'enabled': True,
        'schedule_interval_minutes': 30,  # Cada 30 minutos
        'config': {'description': 'Sincroniza eventos de Google Calendar'}
    },
    'calendar.daily.summary': {
        'enabled': True,
        'schedule_interval_minutes': 1440,  # Diario
        'config': {'description': 'Envía resumen diario de citas del calendario'}
    },
    'meta_ads.cuentas.sync.daily': {
        'enabled': True,
        'schedule_interval_minutes': 1440,  # Diario
        'config': {'description': 'Sincroniza cuentas de Meta Ads diariamente'}
    },
    'meta_ads.anuncios.daily': {
        'enabled': True,
        'schedule_interval_minutes': 1440,  # Diario
        'config': {'description': 'Sincroniza anuncios de Meta Ads y envía reporte'}
    },
    'meta_ads.rechazos.daily': {
        'enabled': True,
        'schedule_interval_minutes': 1440,  # Diario
        'config': {'description': 'Analiza rechazos de anuncios de Meta Ads'}
    },
}


def main():
    """Función principal"""
    print("=" * 80)
    print("⚙️  ACTIVAR Y CONFIGURAR JOBS")
    print("=" * 80)
    print()
    
    try:
        supabase = create_client_from_env()
        
        print(f"📋 Jobs a configurar: {len(JOBS_CONFIG)}")
        print()
        
        for job_name, config in JOBS_CONFIG.items():
            print(f"⚙️  Configurando: {job_name}")
            print(f"   Intervalo: {config['schedule_interval_minutes']} minutos")
            print(f"   Enabled: {config['enabled']}")
            
            try:
                # Verificar si el job existe
                existing = supabase.table('jobs_config') \
                    .select('job_name') \
                    .eq('job_name', job_name) \
                    .execute()
                
                data = {
                    'enabled': config['enabled'],
                    'schedule_interval_minutes': config['schedule_interval_minutes'],
                    'config': config.get('config', {})
                }
                
                if existing.data:
                    # Actualizar
                    supabase.table('jobs_config') \
                        .update(data) \
                        .eq('job_name', job_name) \
                        .execute()
                    print(f"   ✅ Actualizado")
                else:
                    # Crear
                    data['job_name'] = job_name
                    supabase.table('jobs_config') \
                        .insert(data) \
                        .execute()
                    print(f"   ✅ Creado")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print()
        
        print("=" * 80)
        print("✅ Configuración completada")
        print()
        print("💡 Ejecuta 'python scripts/verificar_jobs.py' para verificar el estado")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
