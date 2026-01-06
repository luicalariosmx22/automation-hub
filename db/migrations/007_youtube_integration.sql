-- Tabla para almacenar conexiones de YouTube por cliente
CREATE TABLE IF NOT EXISTS youtube_conexiones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES cliente_empresas(id) ON DELETE CASCADE,
    canal_id TEXT NOT NULL,
    canal_titulo TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    access_token TEXT,
    token_expira_en TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(cliente_id, canal_id)
);

-- Índice para búsquedas rápidas por cliente
CREATE INDEX IF NOT EXISTS idx_youtube_conexiones_cliente ON youtube_conexiones(cliente_id);

-- Índice para búsquedas por canal
CREATE INDEX IF NOT EXISTS idx_youtube_conexiones_canal ON youtube_conexiones(canal_id);

-- Comentarios
COMMENT ON TABLE youtube_conexiones IS 'Almacena conexiones OAuth de YouTube por cliente (solo OWNER del canal)';
COMMENT ON COLUMN youtube_conexiones.cliente_id IS 'ID del cliente/empresa que conectó su canal de YouTube';
COMMENT ON COLUMN youtube_conexiones.canal_id IS 'ID del canal de YouTube (channelId)';
COMMENT ON COLUMN youtube_conexiones.canal_titulo IS 'Título/nombre del canal de YouTube';
COMMENT ON COLUMN youtube_conexiones.refresh_token IS 'Token persistente para renovar access_token';
COMMENT ON COLUMN youtube_conexiones.access_token IS 'Token de acceso temporal (cache opcional)';
COMMENT ON COLUMN youtube_conexiones.token_expira_en IS 'Fecha de expiración del access_token';

-- Tabla para registro de videos subidos
CREATE TABLE IF NOT EXISTS youtube_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conexion_id UUID NOT NULL REFERENCES youtube_conexiones(id) ON DELETE CASCADE,
    cliente_id UUID NOT NULL REFERENCES cliente_empresas(id) ON DELETE CASCADE,
    video_id TEXT NOT NULL UNIQUE,
    video_url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT[],
    privacy_status TEXT NOT NULL,
    is_short BOOLEAN,
    duration NUMERIC,
    width INTEGER,
    height INTEGER,
    aspect_ratio NUMERIC,
    upload_status TEXT,
    processing_status TEXT,
    local_video_path TEXT,
    source_type TEXT,
    source_id TEXT,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_youtube_videos_cliente ON youtube_videos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_video_id ON youtube_videos(video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_source ON youtube_videos(source_type, source_id);

-- Comentarios
COMMENT ON TABLE youtube_videos IS 'Registro de videos subidos a YouTube';
COMMENT ON COLUMN youtube_videos.video_id IS 'ID del video en YouTube';
COMMENT ON COLUMN youtube_videos.is_short IS 'Si el video es un YouTube Short (<=180s, vertical/cuadrado)';
COMMENT ON COLUMN youtube_videos.source_type IS 'Origen del video (ej: facebook_post, manual_upload)';
COMMENT ON COLUMN youtube_videos.source_id IS 'ID del origen (ej: post_id de Facebook)';
