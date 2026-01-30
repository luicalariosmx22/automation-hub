-- Agregar job gbp.locations.sync a jobs_config
-- Sincroniza ubicaciones de Google Business Profile cada 24 horas

INSERT INTO jobs_config (
    job_name,
    enabled,
    interval_minutes,
    last_run_at,
    next_run_at,
    created_at,
    updated_at
) VALUES (
    'gbp.locations.sync',
    true,
    1440,  -- 24 horas (1 vez al día)
    NULL,
    NOW(),  -- Ejecutar inmediatamente en la próxima corrida
    NOW(),
    NOW()
)
ON CONFLICT (job_name) DO UPDATE SET
    enabled = EXCLUDED.enabled,
    interval_minutes = EXCLUDED.interval_minutes,
    updated_at = NOW();
