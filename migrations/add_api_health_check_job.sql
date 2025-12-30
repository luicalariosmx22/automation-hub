-- Migración: Agregar job de verificación de APIs/Tokens
-- Fecha: 2025-12-30
-- Descripción: Job que verifica el estado de todos los tokens y APIs y envía alertas por Telegram

-- Insertar el job en jobs_config
INSERT INTO jobs_config (
    job_name,
    enabled,
    schedule_interval_minutes,
    next_run_at,
    config
) VALUES (
    'api.health_check',
    true,
    720,  -- Cada 12 horas (2 veces al día: 8 AM y 8 PM aproximadamente)
    NOW(),
    '{
        "descripcion": "Verificación de estado de todos los tokens y APIs (OpenAI, DeepSeek, Gemini, Google OAuth GBP, Meta, Telegram, Supabase, TikTok, SMTP, Railway, Encryption)",
        "notify_on_success": false,
        "notify_on_failure": true,
        "servicios_verificar": [
            "OpenAI API",
            "DeepSeek API",
            "Gemini API",
            "Google OAuth (GBP)",
            "Meta/Facebook API",
            "Meta App Config",
            "Meta Webhook Config",
            "Telegram Bot",
            "Supabase",
            "TikTok API",
            "SMTP Gmail",
            "Railway Config",
            "Encryption Key"
        ]
    }'::jsonb
)
ON CONFLICT (job_name) DO UPDATE SET
    enabled = EXCLUDED.enabled,
    schedule_interval_minutes = EXCLUDED.schedule_interval_minutes,
    config = EXCLUDED.config,
    updated_at = NOW();
