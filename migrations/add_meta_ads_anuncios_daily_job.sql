-- Migración: Agregar job de sincronización de anuncios Meta Ads con alertas
-- Fecha: 2025-12-20
-- Descripción: Job que sincroniza anuncios diariamente y envía alertas por Telegram

INSERT INTO public.jobs_config (
    nombre_job,
    descripcion,
    tipo,
    intervalo_ejecucion,
    hora_ejecucion,
    dias_semana,
    activo,
    prioridad,
    timeout_segundos,
    max_reintentos,
    notificar_errores,
    notificar_exito,
    tags
) VALUES (
    'meta_ads.anuncios.daily',
    'Sincroniza anuncios de Meta Ads diariamente y envía análisis por Telegram',
    'scheduled',
    'daily',
    '02:00:00',
    ARRAY['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
    true,
    95,
    1800,
    2,
    true,
    false,
    ARRAY['meta_ads', 'sync', 'telegram', 'alertas']
)
ON CONFLICT (nombre_job) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    intervalo_ejecucion = EXCLUDED.intervalo_ejecucion,
    hora_ejecucion = EXCLUDED.hora_ejecucion,
    dias_semana = EXCLUDED.dias_semana,
    prioridad = EXCLUDED.prioridad,
    timeout_segundos = EXCLUDED.timeout_segundos,
    max_reintentos = EXCLUDED.max_reintentos,
    notificar_errores = EXCLUDED.notificar_errores,
    notificar_exito = EXCLUDED.notificar_exito,
    tags = EXCLUDED.tags;

-- Comentarios
COMMENT ON TABLE public.jobs_config IS 'Configuración de jobs programados del sistema';
