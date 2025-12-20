"""
Script para aplicar todas las migraciones de Meta Ads Daily
Este script debe ejecutarse en Supabase SQL Editor
"""

print("""
================================================================================
INSTRUCCIONES PARA APLICAR MIGRACIONES DE META ADS DAILY
================================================================================

Ejecuta los siguientes archivos SQL en Supabase SQL Editor en este orden:

1. migrations/add_meta_ads_daily_extra_fields.sql
   - Agrega 32 columnas nuevas (26 métricas + 6 demográficos)
   - Tiempo estimado: 5 segundos
   
2. migrations/add_meta_ads_demographics_job.sql
   - Configura el job meta_ads_demographics_sync
   - Se ejecutará diariamente a la 1:30 AM
   - Tiempo estimado: 2 segundos

================================================================================
PASOS:
================================================================================

1. Ve a Supabase Dashboard → SQL Editor
2. Copia el contenido de migrations/add_meta_ads_daily_extra_fields.sql
3. Pégalo y ejecuta
4. Verifica que diga "Success. No rows returned"
5. Copia el contenido de migrations/add_meta_ads_demographics_job.sql
6. Pégalo y ejecuta
7. Verifica que diga "Success" 

================================================================================
VERIFICACIÓN DESPUÉS DE MIGRACIÓN:
================================================================================

Ejecuta este query para verificar las nuevas columnas:

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'meta_ads_anuncios_daily'
AND column_name IN (
  'video_30_sec_watched', 'age', 'gender', 'region', 
  'device_platform', 'cost_per_unique_click_value'
)
ORDER BY column_name;

Deberías ver 6 columnas.

================================================================================
VERIFICAR JOB:
================================================================================

SELECT nombre_job, activo, calendario, prioridad 
FROM jobs_config 
WHERE nombre_job = 'meta_ads_demographics_sync';

Debería mostrar 1 registro con activo=true

================================================================================
PROBAR SINCRONIZACIÓN:
================================================================================

Después de aplicar las migraciones, ejecuta:

python src/automation_hub/jobs/meta_ads_demographics_sync.py

Esto sincronizará los datos demográficos para ayer.

================================================================================
""")

# Mostrar archivos de migración
import os
from pathlib import Path

root_dir = Path(__file__).parent.parent
migrations_dir = root_dir / 'migrations'

print("\nARCHIVOS DE MIGRACIÓN DISPONIBLES:")
print("=" * 80)

migrations = [
    'add_meta_ads_daily_extra_fields.sql',
    'add_meta_ads_demographics_job.sql'
]

for migration in migrations:
    file_path = migrations_dir / migration
    if file_path.exists():
        size = file_path.stat().st_size
        print(f"  ✓ {migration} ({size} bytes)")
    else:
        print(f"  ✗ {migration} - NO ENCONTRADO")

print("\n" + "=" * 80)
print("\n¿Listo para continuar? Copia y ejecuta los SQL en Supabase Dashboard\n")
