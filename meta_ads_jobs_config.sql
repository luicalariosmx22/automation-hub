-- Configuración de jobs para Meta Ads Sync
-- 
-- meta_ads_daily_sync: Sincronización diaria a las 2 AM (120 minutos después de medianoche)
-- meta_ads_weekly_report: Reportes semanales los Lunes a las 3 AM (7 días = 10080 minutos, offset 180 min)

INSERT INTO "public"."jobs_config" 
("job_name", "enabled", "schedule_interval_minutes", "last_run_at", "next_run_at", "config", "created_at", "updated_at") 
VALUES 
(
    'meta_ads_daily_sync', 
    'true', 
    '1440',  -- 24 horas = 1440 minutos (diario)
    NULL,    -- Nunca ejecutado
    '2025-12-20 02:00:00+00',  -- Primera ejecución: mañana a las 2 AM UTC
    '{"description": "Sincronización diaria de datos de Meta Ads", "timezone": "UTC", "target_hour": 2}',
    NOW(),
    NOW()
),
(
    'meta_ads_weekly_report', 
    'true', 
    '10080',  -- 7 días = 10080 minutos (semanal)
    NULL,     -- Nunca ejecutado
    '2025-12-23 03:00:00+00',  -- Primera ejecución: próximo Lunes a las 3 AM UTC
    '{"description": "Generación de reportes semanales de Meta Ads", "timezone": "UTC", "target_hour": 3, "target_weekday": 1}',
    NOW(),
    NOW()
);

-- Verificar inserción
SELECT 
    job_name, 
    enabled, 
    schedule_interval_minutes,
    next_run_at,
    config->>'description' as description
FROM "public"."jobs_config" 
WHERE job_name IN ('meta_ads_daily_sync', 'meta_ads_weekly_report')
ORDER BY job_name;