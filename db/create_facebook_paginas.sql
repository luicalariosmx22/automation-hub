-- Tabla de páginas de Facebook vinculadas a empresas
create table public.facebook_paginas (
  id serial not null,
  page_id character varying(50) not null,
  nombre_pagina character varying(255) not null,
  username character varying(100) null,
  categoria character varying(100) null,
  descripcion text null,
  seguidores integer null default 0,
  likes integer null default 0,
  website character varying(500) null,
  telefono character varying(50) null,
  email character varying(100) null,
  direccion text null,
  ciudad character varying(100) null,
  pais character varying(100) null,
  foto_perfil_url text null,
  foto_portada_url text null,
  verificada boolean null default false,
  activa boolean null default true,
  estado_webhook character varying(20) null default 'activa'::character varying,
  creado_en timestamp with time zone null default now(),
  actualizado_en timestamp with time zone null default now(),
  access_token_valido boolean null default true,
  ultima_sincronizacion timestamp with time zone null,
  permisos_disponibles text[] null,
  nombre_cliente character varying(255) null,
  empresa character varying(255) null,
  empresa_id uuid null,
  access_token text null,
  nombre_nora text null,
  constraint facebook_paginas_pkey primary key (id),
  constraint unique_page_id unique (page_id),
  constraint facebook_paginas_empresa_id_fkey foreign key (empresa_id) references cliente_empresas (id),
  constraint facebook_paginas_estado_webhook_check check (
    (estado_webhook)::text = any (
      array['activa'::character varying, 'pausada'::character varying, 'excluida'::character varying]::text[]
    )
  )
) tablespace pg_default;

-- Índices
create index if not exists idx_facebook_paginas_nombre_nora 
  on public.facebook_paginas using btree (nombre_nora);

create index if not exists idx_facebook_paginas_page_nora 
  on public.facebook_paginas using btree (page_id, nombre_nora);

create index if not exists idx_facebook_paginas_page_id 
  on public.facebook_paginas using btree (page_id);

create index if not exists idx_facebook_paginas_estado 
  on public.facebook_paginas using btree (estado_webhook);

create index if not exists idx_facebook_paginas_activa 
  on public.facebook_paginas using btree (activa);

create index if not exists idx_facebook_paginas_nombre 
  on public.facebook_paginas using btree (nombre_pagina);

-- Comentarios
comment on table public.facebook_paginas is 'Páginas de Facebook vinculadas a empresas';
comment on column public.facebook_paginas.empresa_id is 'ID de la empresa dueña de la página';
comment on column public.facebook_paginas.estado_webhook is 'Estado del webhook para esta página';
