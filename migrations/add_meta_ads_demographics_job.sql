-- Configuración para el job de sincronización demográfica de Meta Ads
-- Se ejecuta DESPUÉS del job meta_ads_cuentas_sync_daily

INSERT INTO public.jobs_config (
    nombre_job,
    descripcion,
    modulo,
    funcion,
    calendario,
    activo,
    prioridad,
    timeout_segundos,
    reintentos_max,
    notificar_en
) VALUES (
    'meta_ads_demographics_sync',
    'Sincroniza datos demográficos (edad, género, región, dispositivo) de anuncios de Meta Ads. Se ejecuta después del sync diario para complementar los datos.',
    'src.automation_hub.jobs.meta_ads_demographics_sync',
    'run',
    'diario',
    true,
    80,  -- Menor prioridad que meta_ads_cuentas_sync_daily (90)
    1800,  -- 30 minutos
    2,
    ARRAY['error']
)
ON CONFLICT (nombre_job) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    modulo = EXCLUDED.modulo,
    funcion = EXCLUDED.funcion,
    calendario = EXCLUDED.calendario,
    prioridad = EXCLUDED.prioridad,
    timeout_segundos = EXCLUDED.timeout_segundos,
    reintentos_max = EXCLUDED.reintentos_max;

-- Configurar horario de ejecución (1:30 AM, después del daily sync a las 1:00 AM)
UPDATE public.jobs_config
SET parametros = jsonb_build_object(
    'hora_ejecucion', '01:30',
    'zona_horaria', 'America/Hermosillo',
    'breakdowns', ARRAY['age', 'gender', 'region', 'device_platform']
)
WHERE nombre_job = 'meta_ads_demographics_sync';
