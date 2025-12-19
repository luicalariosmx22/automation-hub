-- Agregar el nuevo job de sincronización de cuentas Meta Ads
INSERT INTO jobs_config (job_name, enabled, schedule_interval_minutes, next_run_at, config) VALUES
  ('meta_ads.cuentas.sync.daily', true, 1440, NOW(), '{"descripcion": "Sincroniza estado de cuentas publicitarias y detecta desactivaciones"}'::jsonb)
ON CONFLICT (job_name) DO NOTHING;
