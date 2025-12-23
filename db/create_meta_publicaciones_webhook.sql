-- Tabla para almacenar publicaciones recibidas por webhook de Meta
create table public.meta_publicaciones_webhook (
  id bigserial not null,
  page_id character varying(50) not null,
  post_id character varying(100) not null,
  mensaje text null,
  tipo_item character varying(50) null,
  created_time bigint null,
  webhook_data jsonb null,
  procesada boolean null default false,
  procesada_en timestamp with time zone null,
  creada_en timestamp with time zone null default now(),
  imagen_url text null,
  imagen_local text null,
  imagen_descargada_en timestamp with time zone null,
  nombre_nora character varying(100) not null,
  constraint meta_publicaciones_webhook_pkey primary key (id),
  constraint meta_publicaciones_webhook_post_id_key unique (post_id),
  constraint meta_publicaciones_webhook_page_id_check check (((page_id)::text <> ''::text)),
  constraint meta_publicaciones_webhook_post_id_check check (((post_id)::text <> ''::text))
) tablespace pg_default;

-- Índices para optimizar consultas
create index if not exists idx_meta_pub_webhook_nora_post 
  on public.meta_publicaciones_webhook 
  using btree (nombre_nora, post_id) 
  tablespace pg_default;

create index if not exists idx_meta_publicaciones_webhook_page_id 
  on public.meta_publicaciones_webhook 
  using btree (page_id) 
  tablespace pg_default;

create index if not exists idx_meta_publicaciones_webhook_procesada 
  on public.meta_publicaciones_webhook 
  using btree (procesada) 
  tablespace pg_default;

create index if not exists idx_meta_publicaciones_webhook_created 
  on public.meta_publicaciones_webhook 
  using btree (creada_en) 
  tablespace pg_default;

create index if not exists idx_meta_publicaciones_webhook_post_created 
  on public.meta_publicaciones_webhook 
  using btree (created_time) 
  tablespace pg_default;

create index if not exists idx_meta_pub_imagen_url 
  on public.meta_publicaciones_webhook 
  using btree (imagen_url) 
  tablespace pg_default
where (imagen_url is not null);

create index if not exists idx_meta_pub_imagen_local 
  on public.meta_publicaciones_webhook 
  using btree (imagen_local) 
  tablespace pg_default
where (imagen_local is not null);

-- Comentarios
comment on table public.meta_publicaciones_webhook is 'Publicaciones de Meta recibidas por webhook';
comment on column public.meta_publicaciones_webhook.page_id is 'ID de la página de Facebook/Instagram';
comment on column public.meta_publicaciones_webhook.post_id is 'ID único de la publicación';
comment on column public.meta_publicaciones_webhook.mensaje is 'Texto de la publicación';
comment on column public.meta_publicaciones_webhook.tipo_item is 'Tipo de publicación (photo, video, status, etc)';
comment on column public.meta_publicaciones_webhook.created_time is 'Timestamp Unix de creación';
comment on column public.meta_publicaciones_webhook.webhook_data is 'Datos completos del webhook en JSON';
comment on column public.meta_publicaciones_webhook.procesada is 'Indica si la publicación ya fue procesada';
comment on column public.meta_publicaciones_webhook.imagen_url is 'URL de la imagen original';
comment on column public.meta_publicaciones_webhook.imagen_local is 'Ruta local de la imagen descargada';
comment on column public.meta_publicaciones_webhook.nombre_nora is 'Identificador del tenant';
