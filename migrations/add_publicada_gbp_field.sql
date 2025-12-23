-- Agregar campo para trackear publicaciones en GBP
ALTER TABLE meta_publicaciones_webhook 
ADD COLUMN IF NOT EXISTS publicada_gbp BOOLEAN DEFAULT FALSE;

-- Índice para mejorar performance
CREATE INDEX IF NOT EXISTS idx_meta_publicaciones_publicada_gbp 
ON meta_publicaciones_webhook(publicada_gbp) 
WHERE publicada_gbp = FALSE;