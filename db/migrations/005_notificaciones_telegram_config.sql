-- Tabla de configuración de notificaciones por Telegram
-- Permite configurar destinatarios por cliente, jobs y prioridades

CREATE TABLE IF NOT EXISTS notificaciones_telegram_config (
    id BIGSERIAL PRIMARY KEY,
    
    -- Destinatario
    nombre_nora TEXT NOT NULL,  -- Cliente al que pertenece
    chat_id TEXT NOT NULL,       -- Chat ID de Telegram (usuario o grupo)
    nombre_contacto TEXT,        -- Nombre descriptivo del destinatario
    
    -- Filtros de notificaciones
    jobs_permitidos TEXT[],      -- Jobs que pueden notificar (NULL = todos)
                                 -- Ejemplo: ARRAY['gbp.reviews.daily', 'meta_ads.rechazos.daily']
    
    prioridades_permitidas TEXT[], -- Prioridades que notifican (NULL = todas)
                                   -- Ejemplo: ARRAY['alta', 'media']
    
    tipos_alerta_permitidos TEXT[], -- Tipos de alerta específicos (NULL = todos)
                                    -- Ejemplo: ARRAY['cuenta_desactivada', 'meta_ads_rechazados']
    
    -- Control
    activo BOOLEAN DEFAULT TRUE,
    notas TEXT,                  -- Notas internas
    
    -- Auditoría
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_telegram_config_nombre_nora ON notificaciones_telegram_config(nombre_nora);
CREATE INDEX IF NOT EXISTS idx_telegram_config_activo ON notificaciones_telegram_config(activo);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_telegram_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER telegram_config_updated_at
    BEFORE UPDATE ON notificaciones_telegram_config
    FOR EACH ROW
    EXECUTE FUNCTION update_telegram_config_updated_at();

-- Ejemplos de configuración:

-- Admin recibe TODO
INSERT INTO notificaciones_telegram_config (
    nombre_nora, 
    chat_id, 
    nombre_contacto, 
    notas
) VALUES (
    'Sistema',
    '5674082622',  -- Tu chat_id
    'Charlie - Admin',
    'Recibe todas las notificaciones del sistema'
);

-- Cliente específico solo alertas de alta prioridad
-- INSERT INTO notificaciones_telegram_config (
--     nombre_nora, 
--     chat_id, 
--     nombre_contacto,
--     prioridades_permitidas,
--     notas
-- ) VALUES (
--     'Luis',
--     '1234567890',
--     'Luis - Cliente',
--     ARRAY['alta'],
--     'Solo alertas críticas'
-- );

-- Grupo de equipo para jobs específicos
-- INSERT INTO notificaciones_telegram_config (
--     nombre_nora, 
--     chat_id, 
--     nombre_contacto,
--     jobs_permitidos,
--     prioridades_permitidas,
--     notas
-- ) VALUES (
--     'Sistema',
--     '-987654321',
--     'Grupo Meta Ads Team',
--     ARRAY['meta_ads.rechazos.daily', 'meta_ads.cuentas.sync.daily'],
--     ARRAY['alta', 'media'],
--     'Equipo de Meta Ads - solo sus jobs'
-- );

COMMENT ON TABLE notificaciones_telegram_config IS 'Configuración de destinatarios de notificaciones por Telegram';
COMMENT ON COLUMN notificaciones_telegram_config.jobs_permitidos IS 'Lista de jobs que envían notificaciones. NULL = todos los jobs';
COMMENT ON COLUMN notificaciones_telegram_config.prioridades_permitidas IS 'Prioridades que se notifican (alta, media, baja). NULL = todas';
COMMENT ON COLUMN notificaciones_telegram_config.tipos_alerta_permitidos IS 'Tipos específicos de alerta. NULL = todos los tipos';
