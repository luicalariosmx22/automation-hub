-- Tabla para almacenar comentarios de Facebook/Instagram recibidos via webhook
-- Estructura para automatizaciones tipo ManyChat basadas en comentarios

create table public.meta_comentarios_webhook (
  id bigserial not null,
  nombre_nora character varying(100) not null,
  page_id character varying(50) not null,
  post_id character varying(100) not null,
  comment_id character varying(150) not null,
  parent_comment_id character varying(150) null,
  mensaje text null,
  from_id character varying(50) null,
  from_name text null,
  created_time bigint null,
  webhook_data jsonb null,
  procesada boolean not null default false,
  procesada_en timestamp with time zone null,
  creada_en timestamp with time zone not null default now(),
  constraint meta_comentarios_webhook_pkey primary key (id),
  constraint meta_comentarios_webhook_comment_id_uk unique (comment_id),
  constraint meta_comentarios_webhook_post_fk foreign KEY (nombre_nora, post_id) references meta_publicaciones_webhook (nombre_nora, post_id) on delete CASCADE not VALID,
  constraint meta_comentarios_webhook_page_id_check check (((page_id)::text <> ''::text)),
  constraint meta_comentarios_webhook_post_id_check check (((post_id)::text <> ''::text))
) TABLESPACE pg_default;

-- Índices para optimizar consultas
create index IF not exists idx_meta_comentarios_nora_post on public.meta_comentarios_webhook using btree (nombre_nora, post_id) TABLESPACE pg_default;

create index IF not exists idx_meta_comentarios_page_id on public.meta_comentarios_webhook using btree (page_id) TABLESPACE pg_default;

create index IF not exists idx_meta_comentarios_procesada on public.meta_comentarios_webhook using btree (procesada) TABLESPACE pg_default;

create index IF not exists idx_meta_comentarios_creada_en on public.meta_comentarios_webhook using btree (creada_en) TABLESPACE pg_default;

create index IF not exists idx_meta_comentarios_created_time on public.meta_comentarios_webhook using btree (created_time) TABLESPACE pg_default;

-- Comentarios sobre campos clave:
-- nombre_nora: Identificador del cliente/empresa
-- page_id: ID de la página de Facebook/Instagram
-- post_id: ID de la publicación donde se hizo el comentario
-- comment_id: ID único del comentario (para evitar duplicados)
-- parent_comment_id: Para respuestas a otros comentarios (null si es comentario principal)
-- mensaje: Contenido del comentario
-- from_id: ID del usuario que comentó
-- from_name: Nombre del usuario que comentó
-- created_time: Timestamp de creación del comentario (epoch)
-- webhook_data: Data completa del webhook para debugging
-- procesada: Flag para marcar si el comentario ya fue procesado por automatizaciones
-- procesada_en: Timestamp de cuándo se procesó el comentario
-- creada_en: Timestamp de cuándo se insertó el registro