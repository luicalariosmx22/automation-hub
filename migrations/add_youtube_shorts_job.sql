-- Crear job para subir videos a YouTube Shorts diariamente
INSERT INTO jobs_config (
    job_name,
    descripcion,
    script_path,
    is_active,
    intervalo_minutos,
    max_retries,
    timeout_seconds,
    prioridad,
    categoria,
    notificar_errores,
    notificar_exito
) VALUES (
    'youtube_shorts_daily',
    'Sube videos de Facebook a YouTube Shorts automáticamente (solo clientes con canal conectado)',
    'src/automation_hub/jobs/youtube_shorts_daily.py',
    true,
    1440, -- Cada 24 horas
    3,
    1800, -- 30 minutos de timeout
    5,
    'integraciones',
    true,
    false
) ON CONFLICT (job_name) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    script_path = EXCLUDED.script_path,
    intervalo_minutos = EXCLUDED.intervalo_minutos,
    max_retries = EXCLUDED.max_retries,
    timeout_seconds = EXCLUDED.timeout_seconds,
    prioridad = EXCLUDED.prioridad,
    categoria = EXCLUDED.categoria;

-- Verificar que se creó
SELECT 
    job_name,
    descripcion,
    is_active,
    intervalo_minutos,
    categoria
FROM jobs_config
WHERE job_name = 'youtube_shorts_daily';
