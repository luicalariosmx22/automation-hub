-- Tabla de Bots de Telegram
CREATE TABLE IF NOT EXISTS telegram_bots (
    id BIGSERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de Templates de Mensajes
CREATE TABLE IF NOT EXISTS telegram_message_templates (
    id BIGSERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    tipo_alerta TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    prioridad TEXT DEFAULT 'media',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de Historial de Notificaciones
CREATE TABLE IF NOT EXISTS telegram_historial (
    id BIGSERIAL PRIMARY KEY,
    bot_id BIGINT REFERENCES telegram_bots(id),
    chat_id TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    tipo_alerta TEXT,
    prioridad TEXT DEFAULT 'media',
    estado TEXT DEFAULT 'enviado', -- enviado, error
    error TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_telegram_bots_activo ON telegram_bots(activo);
CREATE INDEX IF NOT EXISTS idx_telegram_templates_tipo ON telegram_message_templates(tipo_alerta);
CREATE INDEX IF NOT EXISTS idx_telegram_historial_created ON telegram_historial(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telegram_historial_bot ON telegram_historial(bot_id);
CREATE INDEX IF NOT EXISTS idx_telegram_historial_estado ON telegram_historial(estado);

-- Triggers para updated_at
CREATE OR REPLACE FUNCTION update_telegram_bots_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER telegram_bots_updated_at
    BEFORE UPDATE ON telegram_bots
    FOR EACH ROW
    EXECUTE FUNCTION update_telegram_bots_updated_at();

CREATE OR REPLACE FUNCTION update_telegram_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER telegram_templates_updated_at
    BEFORE UPDATE ON telegram_message_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_telegram_templates_updated_at();

-- Datos de ejemplo
INSERT INTO telegram_bots (nombre, token, descripcion) VALUES
('Bot Principal Nora', 'your_token_here', 'Bot principal para notificaciones del sistema')
ON CONFLICT DO NOTHING;

INSERT INTO telegram_message_templates (nombre, tipo_alerta, mensaje, prioridad) VALUES
('Meta Ads - Anuncio Rechazado', 'meta_ads_rechazado', 
'🚨 <b>Anuncio Rechazado</b>

🏢 Cliente: {nombre}
📱 Anuncio ID: {ad_id}
❌ Motivo: {razon}

📅 {fecha}
⚡ Prioridad: {prioridad}', 'alta'),

('GBP - Review Negativa', 'review_negativa',
'⭐ <b>Nueva Review Negativa</b>

🏢 Ubicación: {location_name}
⭐ Calificación: {rating}/5
💬 Comentario: {comment}

📅 {fecha}', 'media'),

('Sistema - Error Job', 'job_error',
'❌ <b>Error en Job</b>

⚙️ Job: {job_name}
📝 Error: {error}

📅 {fecha}
⚡ Revisar inmediatamente', 'alta')
ON CONFLICT DO NOTHING;

COMMENT ON TABLE telegram_bots IS 'Bots de Telegram configurados para enviar notificaciones';
COMMENT ON TABLE telegram_message_templates IS 'Templates personalizables de mensajes de notificación';
COMMENT ON TABLE telegram_historial IS 'Historial de todas las notificaciones enviadas';
