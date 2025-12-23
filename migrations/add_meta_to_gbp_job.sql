-- Agregar job meta.to_gbp.daily a la configuración
INSERT INTO jobs_config (
    job_name,
    enabled,
    schedule_interval_minutes,
    next_run_at,
    config
) VALUES (
    'meta.to_gbp.daily',
    true,
    1440,  -- Diario (cada 24 horas)
    NOW(),
    '{
        "descripcion": "Publica posts de Facebook a Google Business Profile (sincronización diaria)",
        "timeout_seconds": 600,
        "retry_attempts": 2,
        "retry_delay_seconds": 60,
        "tags": ["meta", "gbp", "posts", "facebook", "sync"]
    }'::jsonb
)
ON CONFLICT (job_name) DO UPDATE SET
    enabled = EXCLUDED.enabled,
    schedule_interval_minutes = EXCLUDED.schedule_interval_minutes,
    config = EXCLUDED.config,
    updated_at = NOW();
