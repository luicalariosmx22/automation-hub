-- Script SQL para limpiar URLs de soynoraai.com

-- Primero ver cuántas hay
SELECT 
    COUNT(*) as total_publicaciones_soynoraai,
    'Publicaciones con URLs de soynoraai.com' as descripcion
FROM meta_publicaciones_webhook 
WHERE imagen_local LIKE '%soynoraai.com%';

-- Ver algunos ejemplos
SELECT 
    id,
    page_id,
    imagen_local,
    created_at
FROM meta_publicaciones_webhook 
WHERE imagen_local LIKE '%soynoraai.com%'
ORDER BY created_at DESC
LIMIT 10;

-- Para ejecutar la limpieza, descomenta las siguientes líneas:
/*
UPDATE meta_publicaciones_webhook 
SET imagen_local = NULL,
    updated_at = NOW()
WHERE imagen_local LIKE '%soynoraai.com%';
*/

-- Verificar después de la limpieza
/*
SELECT 
    COUNT(*) as total_despues_limpieza
FROM meta_publicaciones_webhook 
WHERE imagen_local LIKE '%soynoraai.com%';
*/