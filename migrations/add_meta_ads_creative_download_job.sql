-- Agregar job para descarga de creativos de anuncios Meta Ads
-- Este job descarga imágenes de creativos desde webhooks de Meta Ads a Supabase Storage

INSERT INTO jobs_config (
    job_name,
    descripcion,
    intervalo_minutos,
    is_active,
    categoria,
    prioridad,
    timeout_segundos,
    max_reintentos,
    parametros
) VALUES (
    'meta_ads_creative_download_daily',
    'Descarga creativos (imágenes) de anuncios Meta Ads a Supabase Storage',
    30,  -- Cada 30 minutos
    true,
    'meta',
    40,  -- Prioridad media
    600,  -- 10 minutos timeout
    3,
    '{
        "batch_size": 100,
        "bucket_name": "meta-webhooks"
    }'::jsonb
)
ON CONFLICT (job_name) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    intervalo_minutos = EXCLUDED.intervalo_minutos,
    categoria = EXCLUDED.categoria,
    prioridad = EXCLUDED.prioridad,
    timeout_segundos = EXCLUDED.timeout_segundos,
    max_reintentos = EXCLUDED.max_reintentos,
    parametros = EXCLUDED.parametros,
    updated_at = now();
