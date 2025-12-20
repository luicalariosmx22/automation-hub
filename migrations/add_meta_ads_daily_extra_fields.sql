-- Migración: Agregar campos adicionales de Meta Ads API a tabla daily
-- Fecha: 2025-12-19
-- Descripción: Agrega 26 campos adicionales verificados que funcionan con breakdowns

ALTER TABLE public.meta_ads_anuncios_daily
-- Video avanzado (actions arrays convertidas a int)
ADD COLUMN IF NOT EXISTS video_30_sec_watched integer NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS video_p25_watched integer NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS video_p50_watched integer NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS video_p75_watched integer NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS video_p100_watched integer NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS video_avg_time_watched numeric NULL,
ADD COLUMN IF NOT EXISTS video_play_actions_data jsonb NULL,

-- Conversiones (JSONB porque vienen como arrays)
ADD COLUMN IF NOT EXISTS conversions_data jsonb NULL,
ADD COLUMN IF NOT EXISTS conversion_values_data jsonb NULL,
ADD COLUMN IF NOT EXISTS website_purchase_roas_value numeric NULL,
ADD COLUMN IF NOT EXISTS purchase_roas_value numeric NULL,

-- Cost per metrics directos
ADD COLUMN IF NOT EXISTS cost_per_inline_link_click_value numeric NULL,
ADD COLUMN IF NOT EXISTS cost_per_unique_click_value numeric NULL,
ADD COLUMN IF NOT EXISTS cost_per_unique_inline_link_click_value numeric NULL,
ADD COLUMN IF NOT EXISTS cost_per_unique_link_click_value numeric NULL,

-- CTR adicionales
ADD COLUMN IF NOT EXISTS inline_link_click_ctr_value numeric NULL,
ADD COLUMN IF NOT EXISTS unique_link_clicks_ctr_value numeric NULL,

-- Estimated ad recall
ADD COLUMN IF NOT EXISTS estimated_ad_recallers_count integer NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS estimated_ad_recall_rate_value numeric NULL,

-- Thruplay
ADD COLUMN IF NOT EXISTS thruplays_count integer NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS cost_per_thruplay_value numeric NULL,

-- Cost per actions (JSONB - arrays complejos)
ADD COLUMN IF NOT EXISTS cost_per_action_type_data jsonb NULL,
ADD COLUMN IF NOT EXISTS cost_per_conversion_data jsonb NULL,
ADD COLUMN IF NOT EXISTS cost_per_outbound_click_data jsonb NULL,
ADD COLUMN IF NOT EXISTS cost_per_unique_outbound_click_data jsonb NULL,

-- Datos demográficos y geográficos (se llenan con sincronización adicional)
ADD COLUMN IF NOT EXISTS age text NULL,
ADD COLUMN IF NOT EXISTS gender text NULL,
ADD COLUMN IF NOT EXISTS region text NULL,
ADD COLUMN IF NOT EXISTS country text NULL,
ADD COLUMN IF NOT EXISTS device_platform text NULL,
ADD COLUMN IF NOT EXISTS impression_device text NULL;

-- Comentarios para documentación
COMMENT ON COLUMN public.meta_ads_anuncios_daily.video_30_sec_watched IS 'Videos vistos 30 segundos (de video_30_sec_watched_actions)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.video_p25_watched IS 'Videos vistos 25% (de video_p25_watched_actions)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.video_p50_watched IS 'Videos vistos 50% (de video_p50_watched_actions)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.video_p75_watched IS 'Videos vistos 75% (de video_p75_watched_actions)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.video_p100_watched IS 'Videos vistos 100% (de video_p100_watched_actions)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.video_avg_time_watched IS 'Tiempo promedio de visualización de video';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.video_play_actions_data IS 'Acciones de reproducción de video (JSONB)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.conversions_data IS 'Conversiones completas (JSONB array)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.conversion_values_data IS 'Valores de conversiones (JSONB array)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.cost_per_action_type_data IS 'Costo por tipo de acción (JSONB array)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.age IS 'Rango de edad (18-24, 25-34, etc.) - Se llena con sync demográfico';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.gender IS 'Género (male, female, unknown) - Se llena con sync demográfico';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.region IS 'Región/Estado - Se llena con sync demográfico';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.country IS 'País - Se llena con sync demográfico';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.device_platform IS 'Plataforma dispositivo (mobile_app, desktop, etc.)';
COMMENT ON COLUMN public.meta_ads_anuncios_daily.impression_device IS 'Tipo dispositivo (android_smartphone, iphone, etc.)';
