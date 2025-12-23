-- Tabla de ubicaciones de Google Business Profile
create table public.gbp_locations (
  id uuid not null default gen_random_uuid(),
  nombre_nora text not null,
  api_id uuid null,
  account_name text not null,
  location_name text not null,
  location_id text null,
  title text null,
  primary_category text null,
  phone text null,
  website text null,
  address jsonb null,
  lat numeric(10, 7) null,
  lng numeric(10, 7) null,
  open_info jsonb null,
  state text null,
  metadata jsonb null,
  raw jsonb null,
  synced_at timestamp without time zone null,
  created_at timestamp without time zone not null default now(),
  updated_at timestamp without time zone not null default now(),
  additional_phones text[] null,
  categories jsonb null,
  description text null,
  service_area jsonb null,
  special_hours jsonb null,
  more_hours jsonb null,
  place_id text null,
  maps_uri text null,
  duplicate_location boolean null,
  activa boolean not null default true,
  dias_programados jsonb null default '{"dias": []}'::jsonb,
  canonical_id text null,
  empresa_id uuid null,
  constraint gbp_locations_pkey primary key (id),
  constraint gbp_locations_uq unique (nombre_nora, location_id),
  constraint gbp_locations_api_id_fkey foreign key (api_id) references apis_registradas (id) on delete set null,
  constraint gbp_locations_empresa_id_fkey foreign key (empresa_id) references cliente_empresas (id) on delete set null
) tablespace pg_default;

-- Índices
create index if not exists gbp_locations_idx_activa 
  on public.gbp_locations using btree (nombre_nora, activa);

create index if not exists idx_gbp_locations_dias_programados 
  on public.gbp_locations using gin (dias_programados);

create index if not exists gbp_locations_idx_nora 
  on public.gbp_locations using btree (nombre_nora);

create index if not exists gbp_locations_idx_account 
  on public.gbp_locations using btree (account_name);

create index if not exists gbp_locations_idx_title 
  on public.gbp_locations using btree (title);

create index if not exists gbp_locations_idx_location_id 
  on public.gbp_locations using btree (location_id);

create index if not exists gbp_locations_idx_place_id 
  on public.gbp_locations using btree (place_id);

create unique index if not exists gbp_locations_uq_canonical 
  on public.gbp_locations using btree (nombre_nora, canonical_id);

create index if not exists idx_gbp_locations_location_name 
  on public.gbp_locations using btree (nombre_nora, location_name);

create index if not exists idx_gbp_locations_place_id_nora 
  on public.gbp_locations using btree (nombre_nora, place_id)
where (place_id is not null and place_id <> ''::text);

create index if not exists idx_gbp_locations_activa_nora 
  on public.gbp_locations using btree (nombre_nora, activa)
where (activa = true);

create index if not exists idx_gbp_locations_empresa_id 
  on public.gbp_locations using btree (nombre_nora, empresa_id)
where (empresa_id is not null);

create index if not exists idx_gbp_locations_sin_empresa 
  on public.gbp_locations using btree (nombre_nora, activa)
where (empresa_id is null and activa = true);

-- Comentarios
comment on table public.gbp_locations is 'Ubicaciones de Google Business Profile vinculadas a empresas';
comment on column public.gbp_locations.empresa_id is 'ID de la empresa dueña de la ubicación';
comment on column public.gbp_locations.dias_programados is 'Días de la semana para publicar automáticamente';
