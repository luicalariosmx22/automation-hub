-- Migración: Agregar job de automatización de comentarios de Meta
-- Fecha: 2025-12-31
-- Descripción: Job que procesa comentarios de Facebook/Instagram y ejecuta automatizaciones tipo ManyChat

INSERT INTO jobs_config (
    job_name,
    enabled,
    schedule_interval_minutes,
    config
) VALUES (
    'meta.comentarios.automation',
    true,
    5,  -- Ejecutar cada 5 minutos para respuesta rápida
    '{
        "description": "Automatización de comentarios de Meta (Facebook/Instagram) tipo ManyChat",
        "features": [
            "Detección de palabras clave en comentarios",
            "Respuestas automáticas",
            "Notificaciones al administrador",
            "Alertas urgentes para comentarios negativos",
            "Detección de leads calificados"
        ],
        "reglas_configuradas": 4,
        "acciones_soportadas": [
            "responder_automatico",
            "notificar_admin", 
            "alerta_urgente",
            "lead_calificado"
        ],
        "batch_size": 50,
        "max_comentarios_por_ejecucion": 200,
        "ventana_procesamiento_horas": 24
    }'
)
ON CONFLICT (job_name) 
DO UPDATE SET
    enabled = EXCLUDED.enabled,
    schedule_interval_minutes = EXCLUDED.schedule_interval_minutes,
    config = EXCLUDED.config,
    updated_at = NOW();