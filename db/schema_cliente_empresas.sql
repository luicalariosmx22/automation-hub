-- Schema de la tabla cliente_empresas
create table public.cliente_empresas (
  id uuid not null default gen_random_uuid (),
  nombre_nora text not null,
  nombre_empresa text not null,
  giro text null,
  razon_social text null,
  rfc text null,
  email_empresa text null,
  telefono_empresa text null,
  sitio_web text null,
  logo_url text null,
  ubicacion text null,
  ciudad text null,
  estado text null,
  pais text null,
  redes jsonb null,
  accesos jsonb null,
  representante_legal text null,
  email_representante text null,
  telefono_representante text null,
  fecha_alta date null,
  fecha_baja date null,
  notas text null,
  creado_en timestamp without time zone null default now(),
  actualizado_en timestamp without time zone null default now(),
  cliente_id uuid null,
  activo boolean null default true,
  tipo text null,
  brief text null,
  password_hash text null,
  logos jsonb null default '{"claro": null, "oscuro": null, "favicon": null, "vertical": null, "principal": null, "horizontal": null}'::jsonb,
  metodos_pago jsonb null default '[]'::jsonb,
  colores_marca jsonb null default '{"acento": "#10B981", "primario": "#6366F1", "secundario": "#06B6D4"}'::jsonb,
  servicios_wordpress boolean null default false,
  servicios_meta_ads boolean null default false,
  servicios_google_maps boolean null default false,
  servicios_google_ads boolean null default false,
  servicios_contenidos_ia boolean null default false,
  servicios_planeacion boolean null default false,
  constraint cliente_empresas_pkey primary key (id)
) TABLESPACE pg_default;

create unique INDEX IF not exists idx_cliente_empresas_tenant_email_ci on public.cliente_empresas using btree (nombre_nora, lower(email_empresa)) TABLESPACE pg_default
where
  (email_empresa is not null);

create index IF not exists idx_cliente_empresas_email_ci on public.cliente_empresas using btree (lower(email_empresa)) TABLESPACE pg_default
where
  (email_empresa is not null);

create index IF not exists idx_cliente_empresas_activo on public.cliente_empresas using btree (activo) TABLESPACE pg_default;

create index IF not exists idx_cliente_empresas_nombre_nora on public.cliente_empresas using btree (nombre_nora) TABLESPACE pg_default;

create index IF not exists idx_cliente_empresas_cliente_id on public.cliente_empresas using btree (cliente_id) TABLESPACE pg_default;

create index IF not exists idx_cliente_empresas_nombre_nora_activo on public.cliente_empresas using btree (nombre_nora, activo) TABLESPACE pg_default;