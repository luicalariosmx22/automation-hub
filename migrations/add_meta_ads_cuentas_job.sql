-- Agregar job de sincronización de cuentas publicitarias Meta Ads
INSERT INTO jobs_config (job_name, enabled, schedule_interval_minutes, next_run_at, config) 
VALUES (
  'meta_ads.cuentas.daily',
  true,
  1440,  -- 24 horas (diario)
  NOW(),
  jsonb_build_object(
    'descripcion', 'Sincroniza información de cuentas publicitarias de Meta Ads',
    'dependencias', ARRAY['META_ADS_ACCESS_TOKEN', 'SUPABASE_URL', 'SUPABASE_KEY']
  )
)
ON CONFLICT (job_name) DO UPDATE SET
  enabled = EXCLUDED.enabled,
  schedule_interval_minutes = EXCLUDED.schedule_interval_minutes,
  config = EXCLUDED.config;

-- Verificar jobs configurados
SELECT job_name, enabled, schedule_interval_minutes, next_run_at
FROM jobs_config
ORDER BY job_name;
