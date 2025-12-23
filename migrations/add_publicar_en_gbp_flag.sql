-- Agregar campo para controlar qué páginas de Facebook publican automáticamente en GBP
ALTER TABLE facebook_paginas 
ADD COLUMN publicar_en_gbp BOOLEAN DEFAULT FALSE;

-- Comentario explicativo
COMMENT ON COLUMN facebook_paginas.publicar_en_gbp IS 'Indica si los posts de esta página deben publicarse automáticamente en Google Business Profile';

-- Crear índice para mejorar consultas del job
CREATE INDEX idx_facebook_paginas_publicar_en_gbp ON facebook_paginas(publicar_en_gbp) WHERE publicar_en_gbp = TRUE;
