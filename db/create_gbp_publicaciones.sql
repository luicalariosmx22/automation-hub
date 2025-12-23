-- Tabla de publicaciones realizadas en Google Business Profile
create table public.gbp_publicaciones (
  id uuid not null default gen_random_uuid(),
  nombre_nora text not null,
  location_name text not null,
  tipo text not null,
  contenido text not null,
  cta_tipo text null,
  cta_url text null,
  fecha_inicio timestamp with time zone null,
  fecha_fin timestamp with time zone null,
  estado text not null default 'pendiente'::text,
  gbp_post_name text null,
  error_mensaje text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  published_at timestamp with time zone null,
  imagen_url text null,
  constraint gbp_publicaciones_pkey primary key (id),
  constraint gbp_publicaciones_cta_tipo_check check (
    cta_tipo = any (array['BOOK'::text, 'ORDER'::text, 'LEARN_MORE'::text, 'SIGN_UP'::text, 
                         'CALL'::text, 'BUY'::text, 'GET_OFFER'::text, 'SHOP_NOW'::text])
  ),
  constraint gbp_publicaciones_estado_check check (
    estado = any (array['pendiente'::text, 'publicada'::text, 'error'::text, 'eliminada'::text])
  ),
  constraint gbp_publicaciones_tipo_check check (
    tipo = any (array['STANDARD'::text, 'EVENT'::text, 'OFFER'::text, 'ALERT'::text, 'FROM_FACEBOOK'::text])
  )
) tablespace pg_default;

-- Índices
create index if not exists idx_gbp_publicaciones_nora 
  on public.gbp_publicaciones using btree (nombre_nora);

create index if not exists idx_gbp_publicaciones_location 
  on public.gbp_publicaciones using btree (location_name);

create index if not exists idx_gbp_publicaciones_estado 
  on public.gbp_publicaciones using btree (estado);

create index if not exists idx_gbp_publicaciones_created 
  on public.gbp_publicaciones using btree (created_at desc);

create index if not exists idx_gbp_publicaciones_nora_created 
  on public.gbp_publicaciones using btree (nombre_nora, created_at desc);

-- Comentarios
comment on table public.gbp_publicaciones is 'Log de publicaciones creadas en Google Business Profile';
comment on column public.gbp_publicaciones.tipo is 'Tipo de publicación (FROM_FACEBOOK indica que viene de Meta)';
comment on column public.gbp_publicaciones.estado is 'Estado de la publicación';
comment on column public.gbp_publicaciones.gbp_post_name is 'Nombre del post retornado por la API de GBP';
