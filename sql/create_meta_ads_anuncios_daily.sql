-- Tabla para datos diarios de Meta Ads
-- Adaptada para manejar datos día por día en lugar de rangos de fechas

CREATE TABLE public.meta_ads_anuncios_daily (
  id serial NOT NULL,
  ad_id text NOT NULL,
  nombre_anuncio text NULL,
  importe_gastado numeric NULL,
  id_cuenta_publicitaria text NOT NULL,
  conjunto_id text NULL,
  campana_id text NULL,
  alcance integer NULL,
  impresiones integer NULL,
  interacciones integer NULL,
  clicks integer NULL DEFAULT 0,
  link_clicks integer NULL DEFAULT 0,
  inline_link_clicks integer NULL DEFAULT 0,
  ctr numeric NULL,
  cpc numeric NULL,
  cost_per_unique_click numeric NULL,
  cost_per_unique_inline_link_click numeric NULL,
  unique_clicks integer NULL,
  unique_inline_link_clicks integer NULL,
  frequency numeric NULL,
  quality_ranking text NULL,
  video_plays integer NULL,
  video_plays_15s integer NULL,
  video_avg_watch_time_secs numeric NULL,
  video_completion_rate numeric NULL,
  post_reactions integer NULL,
  shares integer NULL,
  comments integer NULL,
  saves integer NULL,
  page_engagement integer NULL,
  messaging_conversations_started integer NULL,
  video_plays_at_25 integer NULL,
  video_plays_at_50 integer NULL,
  video_plays_at_75 integer NULL,
  video_plays_at_100 integer NULL,
  video_play_actions jsonb NULL,
  video_avg_time_watched_actions numeric NULL,
  post_engagement integer NULL,
  post_comments integer NULL,
  post_shares integer NULL,
  cost_per_messaging_conversation_started numeric NULL,
  cost_per_inline_link_click numeric NULL,
  unique_ctr numeric NULL,
  unique_impressions integer NULL,
  unique_link_clicks integer NULL,
  cost_per_unique_link_click numeric NULL,
  cost_per_click numeric NULL,
  cost_per_1k_impressions numeric NULL,
  cost_per_10_sec_video_view numeric NULL,
  cost_per_2_sec_continuous_video_view numeric NULL,
  cost_per_action_type numeric NULL,
  cost_per_estimated_ad_recallers numeric NULL,
  cost_per_outbound_click numeric NULL,
  cost_per_thruplay numeric NULL,
  cost_per_unique_outbound_click numeric NULL,
  estimated_ad_recallers integer NULL,
  estimated_ad_recall_rate numeric NULL,
  outbound_clicks integer NULL,
  outbound_clicks_ctr numeric NULL,
  thruplay_rate numeric NULL,
  thruplays integer NULL,
  unique_outbound_clicks integer NULL,
  website_ctr numeric NULL,
  website_purchase_roas numeric NULL,
  purchase_roas numeric NULL,
  actions jsonb NULL,
  
  -- Campos de fecha adaptados para datos diarios
  fecha_reporte date NOT NULL,  -- Fecha específica del dato (un solo día)
  fecha_desde date NULL,        -- Fecha desde cuando se acumula el dato (para métricas acumulativas)
  fecha_hasta date NULL,        -- Fecha hasta cuando se acumula el dato (para métricas acumulativas)
  
  nombre_campana text NULL,
  nombre_conjunto text NULL,
  publisher_platform text NOT NULL,
  reproducciones_video_3s integer NULL DEFAULT 0,
  objetivo_campana text NULL,
  status_campana text NULL,
  status_conjunto text NULL,
  status text NULL,
  preview_url text NULL,
  fecha_sincronizacion timestamp without time zone NULL,
  fecha_ultima_actualizacion timestamp without time zone NULL,
  activo boolean NULL DEFAULT true,
  post_engagements numeric NULL DEFAULT 0,
  page_likes numeric NULL DEFAULT 0,
  post_likes numeric NULL DEFAULT 0,
  video_views numeric NULL DEFAULT 0,
  landing_page_views numeric NULL DEFAULT 0,
  add_to_cart numeric NULL DEFAULT 0,
  initiate_checkout numeric NULL DEFAULT 0,
  video_p25_watched numeric NULL DEFAULT 0,
  video_p50_watched numeric NULL DEFAULT 0,
  video_p75_watched numeric NULL DEFAULT 0,
  video_p100_watched numeric NULL DEFAULT 0,
  video_30s_watched numeric NULL DEFAULT 0,
  cost_per_lead numeric NULL DEFAULT 0,
  cost_per_purchase numeric NULL DEFAULT 0,
  cost_per_link_click numeric NULL DEFAULT 0,
  messaging_first_reply integer NULL,
  mensajes_total integer NULL,
  cost_per_message numeric NULL,
  cost_per_messaging_first_reply numeric NULL,
  costo_por_mensaje_total numeric NULL,
  msg_cost_is_calculated boolean NOT NULL DEFAULT false,
  messages_source character varying(16) NULL,
  nombre_nora text NOT NULL,
  
  -- Clave primaria adaptada para datos diarios
  CONSTRAINT meta_ads_anuncios_daily_pkey PRIMARY KEY (
    ad_id,
    fecha_reporte,
    publisher_platform
  ),
  CONSTRAINT fk_anuncios_daily_cuenta FOREIGN KEY (id_cuenta_publicitaria) 
    REFERENCES meta_ads_cuentas (id_cuenta_publicitaria)
) TABLESPACE pg_default;

-- Índices optimizados para consultas diarias
CREATE INDEX IF NOT EXISTS idx_meta_ads_anuncios_daily_activos 
  ON public.meta_ads_anuncios_daily USING btree (activo, id_cuenta_publicitaria) 
  TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_meta_ads_anuncios_daily_sync 
  ON public.meta_ads_anuncios_daily USING btree (fecha_sincronizacion) 
  TABLESPACE pg_default;

CREATE UNIQUE INDEX IF NOT EXISTS meta_ads_anuncios_daily_unique_idx 
  ON public.meta_ads_anuncios_daily USING btree (
    ad_id,
    fecha_reporte,
    publisher_platform
  ) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_meta_ads_anuncios_daily_tenant_performance 
  ON public.meta_ads_anuncios_daily USING btree (
    nombre_nora,
    id_cuenta_publicitaria,
    fecha_reporte
  ) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_meta_ads_anuncios_daily_messaging 
  ON public.meta_ads_anuncios_daily USING btree (nombre_nora, messaging_conversations_started) 
  TABLESPACE pg_default
  WHERE (messaging_conversations_started > 0);

-- Índice adicional para consultas por rango de fechas
CREATE INDEX IF NOT EXISTS idx_meta_ads_anuncios_daily_fecha_rango 
  ON public.meta_ads_anuncios_daily USING btree (
    id_cuenta_publicitaria,
    fecha_reporte,
    activo
  ) TABLESPACE pg_default;

-- Índice para consultas de agregación por campaña/conjunto
CREATE INDEX IF NOT EXISTS idx_meta_ads_anuncios_daily_campana 
  ON public.meta_ads_anuncios_daily USING btree (
    campana_id,
    conjunto_id,
    fecha_reporte
  ) TABLESPACE pg_default;