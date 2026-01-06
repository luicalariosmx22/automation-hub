-- Tabla para almacenar reglas de automatización de comentarios
-- Permite configurar acciones automáticas basadas en palabras clave en comentarios

CREATE TABLE public.meta_comentarios_reglas (
  id bigserial NOT NULL,
  nombre_nora character varying(100) NOT NULL,
  nombre_regla character varying(200) NOT NULL,
  descripcion text NULL,
  
  -- Filtros de aplicación (NULL = aplica a todos)
  page_id character varying(50) NULL,
  post_id character varying(100) NULL,
  
  -- Condiciones para activar la regla
  palabras_clave jsonb NOT NULL,
  
  -- Acción a ejecutar
  accion character varying(50) NOT NULL,
  parametros jsonb NULL DEFAULT '{}',
  
  -- Control
  activa boolean NOT NULL DEFAULT true,
  prioridad integer NOT NULL DEFAULT 5,
  creada_en timestamp with time zone NOT NULL DEFAULT now(),
  actualizada_en timestamp with time zone NOT NULL DEFAULT now(),
  
  CONSTRAINT meta_comentarios_reglas_pkey PRIMARY KEY (id),
  CONSTRAINT meta_comentarios_reglas_nombre_nora_check CHECK (((nombre_nora)::text <> ''::text)),
  CONSTRAINT meta_comentarios_reglas_accion_check CHECK (
    accion IN ('responder_automatico', 'notificar_admin', 'alerta_urgente', 'lead_calificado', 'enviar_mensaje_privado')
  ),
  CONSTRAINT meta_comentarios_reglas_prioridad_check CHECK (prioridad >= 1 AND prioridad <= 10)
) TABLESPACE pg_default;

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_meta_comentarios_reglas_nora 
ON public.meta_comentarios_reglas USING btree (nombre_nora) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_meta_comentarios_reglas_page_id 
ON public.meta_comentarios_reglas USING btree (page_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_meta_comentarios_reglas_post_id 
ON public.meta_comentarios_reglas USING btree (post_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_meta_comentarios_reglas_activa 
ON public.meta_comentarios_reglas USING btree (activa) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_meta_comentarios_reglas_prioridad 
ON public.meta_comentarios_reglas USING btree (prioridad) TABLESPACE pg_default;

-- Índice compuesto para consultas principales
CREATE INDEX IF NOT EXISTS idx_meta_comentarios_reglas_lookup 
ON public.meta_comentarios_reglas USING btree (nombre_nora, activa, prioridad) TABLESPACE pg_default;

-- Trigger para actualizar timestamp
CREATE OR REPLACE FUNCTION update_meta_comentarios_reglas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizada_en = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_meta_comentarios_reglas_updated_at
    BEFORE UPDATE ON public.meta_comentarios_reglas
    FOR EACH ROW
    EXECUTE FUNCTION update_meta_comentarios_reglas_updated_at();

-- Comentarios sobre la estructura
COMMENT ON TABLE public.meta_comentarios_reglas IS 'Reglas de automatización para comentarios de Facebook/Instagram';
COMMENT ON COLUMN public.meta_comentarios_reglas.page_id IS 'ID de página específica (NULL = todas las páginas)';
COMMENT ON COLUMN public.meta_comentarios_reglas.post_id IS 'ID de post específico (NULL = todos los posts)';
COMMENT ON COLUMN public.meta_comentarios_reglas.palabras_clave IS 'Array JSON de palabras/frases que activan la regla';
COMMENT ON COLUMN public.meta_comentarios_reglas.parametros IS 'Parámetros específicos de la acción en formato JSON';
COMMENT ON COLUMN public.meta_comentarios_reglas.prioridad IS 'Orden de ejecución (1=alta prioridad, 10=baja prioridad)';

-- Datos de ejemplo
INSERT INTO public.meta_comentarios_reglas (
    nombre_nora, nombre_regla, descripcion, page_id, post_id, 
    palabras_clave, accion, parametros, prioridad
) VALUES 
-- Regla global para información
('Sistema', 'Solicitud de Información Global', 'Respuesta automática para solicitudes de información', 
 NULL, NULL, 
 '["info", "información", "precio", "precios", "costo", "cuanto", "disponible"]', 
 'responder_automatico', 
 '{"mensaje": "¡Hola! 👋 Gracias por tu interés. Te enviaré la información por mensaje privado. 📩"}', 
 3),

-- Regla para comentarios negativos (alta prioridad)
('Sistema', 'Detectar Comentarios Negativos', 'Alerta urgente para comentarios negativos', 
 NULL, NULL, 
 '["malo", "pésimo", "terrible", "no funciona", "no sirve", "queja", "horrible"]', 
 'alerta_urgente', 
 '{"prioridad": "alta", "notificar_inmediato": true}', 
 1),

-- Regla para leads calificados
('Sistema', 'Leads Calificados', 'Detección de potenciales compradores', 
 NULL, NULL, 
 '["quiero", "comprar", "adquirir", "me interesa", "necesito", "cotización"]', 
 'lead_calificado', 
 '{"prioridad": "alta", "asignar_vendedor": true}', 
 2),

-- Regla para saludos
('Sistema', 'Saludos de Bienvenida', 'Notificar cuando alguien saluda', 
 NULL, NULL, 
 '["hola", "buenos días", "buenas tardes", "buenas noches", "saludos"]', 
 'notificar_admin', 
 '{"mensaje": "Nuevo saludo detectado - responder manualmente"}', 
 4);