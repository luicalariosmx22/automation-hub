-- Agregar soporte para videos en meta_publicaciones_webhook
-- NOTA: Si los campos ya existen, este script no hace nada (IF NOT EXISTS)

-- Verificar y agregar campos de video (solo si no existen)
DO $$ 
BEGIN
    -- video_local
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'meta_publicaciones_webhook' 
        AND column_name = 'video_local'
    ) THEN
        ALTER TABLE public.meta_publicaciones_webhook ADD COLUMN video_local text NULL;
    END IF;
    
    -- video_url_public
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'meta_publicaciones_webhook' 
        AND column_name = 'video_url_public'
    ) THEN
        ALTER TABLE public.meta_publicaciones_webhook ADD COLUMN video_url_public text NULL;
    END IF;
    
    -- video_storage_path
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'meta_publicaciones_webhook' 
        AND column_name = 'video_storage_path'
    ) THEN
        ALTER TABLE public.meta_publicaciones_webhook ADD COLUMN video_storage_path text NULL;
    END IF;
    
    -- video_descargado_en
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'meta_publicaciones_webhook' 
        AND column_name = 'video_descargado_en'
    ) THEN
        ALTER TABLE public.meta_publicaciones_webhook ADD COLUMN video_descargado_en timestamp with time zone NULL;
    END IF;
END $$;

-- Índices para optimizar consultas de videos
CREATE INDEX IF NOT EXISTS idx_meta_pub_video_local 
  ON public.meta_publicaciones_webhook 
  USING btree (video_local) 
  TABLESPACE pg_default
WHERE (video_local IS NOT NULL);

CREATE INDEX IF NOT EXISTS idx_meta_pub_tipo_pendiente 
  ON public.meta_publicaciones_webhook 
  USING btree (tipo_item, procesada) 
  TABLESPACE pg_default
WHERE (imagen_url IS NOT NULL AND (imagen_local IS NULL OR video_local IS NULL));

-- Comentarios (solo si los campos fueron creados)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'meta_publicaciones_webhook' 
        AND column_name = 'video_local'
    ) THEN
        COMMENT ON COLUMN public.meta_publicaciones_webhook.video_local IS 'URL pública del video descargado en Supabase Storage';
        COMMENT ON COLUMN public.meta_publicaciones_webhook.video_url_public IS 'URL pública del video (alias de video_local)';
        COMMENT ON COLUMN public.meta_publicaciones_webhook.video_storage_path IS 'Ruta del video en Supabase Storage bucket';
        COMMENT ON COLUMN public.meta_publicaciones_webhook.video_descargado_en IS 'Timestamp de cuando se descargó el video';
    END IF;
END $$;
