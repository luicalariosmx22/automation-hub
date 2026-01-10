-- Agregar job para descarga de media de publicaciones Meta
-- Este job descarga imágenes y videos desde webhooks de Meta a Supabase Storage

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
    'meta_media_download_daily',
    'Descarga imágenes y videos de publicaciones Meta (webhooks) a Supabase Storage',
    15,  -- Cada 15 minutos
    true,
    'meta',
    50,  -- Prioridad media-alta
    600,  -- 10 minutos timeout
    3,
    '{
        "batch_size": 50,
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

-- Comentario
COMMENT ON TABLE jobs_config IS 'Configuración de jobs automatizados del sistema';
