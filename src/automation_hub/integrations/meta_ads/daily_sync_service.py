"""
Servicio para sincronización diaria de Meta Ads a Supabase.

Este servicio está optimizado para trabajar con datos diarios individuales
en lugar de rangos de fechas, usando la tabla meta_ads_anuncios_daily.
"""

import os
import json
import time
import requests
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from ...db.supabase_client import create_client_from_env


class MetaAdsDailySyncService:
    """Servicio para sincronizar datos diarios de Meta Ads a Supabase"""
    
    # API Configuration
    GRAPH_API_VERSION = os.getenv('META_API_VERSION', 'v23.0')
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    
    # Cache configuration
    NAME_CACHE_TTL = int(os.getenv('NAMES_CACHE_TTL', '3600'))
    _name_cache = {}
    
    # Debug configuration
    LOG_DEBUG = os.getenv("META_SYNC_DEBUG", "0") == "1"
    LOG_EVERY = int(os.getenv("META_SYNC_LOG_EVERY", "100") or "100")
    
    # Fields que funcionan CON breakdowns (publisher_platform + action_type)
    # Probados y verificados: 26 campos adicionales disponibles
    INSIGHT_FIELDS = [
        # Identificadores y fechas
        "date_start", "date_stop", "account_id", "campaign_id", "adset_id", "ad_id",
        # Nombres
        "ad_name", "adset_name", "campaign_name",
        # Métricas core
        "impressions", "reach", "clicks", "inline_link_clicks",
        "spend", "cpm", "cpc", "ctr", "unique_ctr",
        # Actions - CRÍTICO para derivar mensajes y engagements
        "actions", "action_values",
        # Unique metrics
        "unique_clicks", "unique_inline_link_clicks",
        # Outbound
        "outbound_clicks", "outbound_clicks_ctr",
        # Website
        "website_ctr",
        
        # === CAMPOS ADICIONALES DISPONIBLES CON BREAKDOWNS ===
        # Video metrics avanzados
        "video_30_sec_watched_actions",
        "video_p25_watched_actions",
        "video_p50_watched_actions",
        "video_p75_watched_actions",
        "video_p100_watched_actions",
        "video_avg_time_watched_actions",
        "video_play_actions",
        "video_thruplay_watched_actions",
        
        # Conversiones
        "conversions",
        "conversion_values",
        "website_purchase_roas",
        "purchase_roas",
        
        # Cost per metrics
        "cost_per_inline_link_click",
        "cost_per_inline_post_engagement",
        "cost_per_unique_click",
        "cost_per_unique_inline_link_click",
        "cost_per_unique_link_click",
        "cost_per_action_type",
        "cost_per_conversion",
        "cost_per_outbound_click",
        "cost_per_unique_outbound_click",
        "cost_per_thruplay",
        
        # CTR metrics
        "inline_link_click_ctr",
        "unique_link_clicks_ctr",
        
        # Recall metrics
        "estimated_ad_recallers",
        "estimated_ad_recall_rate",
    ]
    
    # Action types que representan mensajes
    MSG_TYPES = {
        "onsite_conversion.messaging_conversation_started_7d",
        "onsite_conversion.messaging_conversation_started",
        "messaging_conversation_started_7d",
        "messaging_conversation_started",
        "onsite_conversion.messaging_first_reply",
        "messaging_first_reply",
        "onsite_conversion.total_messaging_connection",
        "total_messaging_connection",
    }
    
    def __init__(self, supabase_client=None):
        """Initialize service with Supabase client"""
        self.supabase = supabase_client or create_client_from_env()
        self.access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
        if not self.access_token:
            raise ValueError("META_ACCESS_REDACTED_TOKEN environment variable is required")
    
    @staticmethod
    def clean_surrogates(text: str) -> str:
        """Limpia caracteres surrogates para evitar errores de encoding UTF-8"""
        if not isinstance(text, str):
            return str(text)
        return text.encode('utf-8', errors='ignore').decode('utf-8')
    
    @staticmethod
    def normalize_account_id(account_id: str) -> str:
        """Normaliza ID de cuenta removiendo prefijo 'act_' si existe"""
        return account_id[4:] if account_id.startswith('act_') else account_id
    
    def _debug(self, msg: str) -> None:
        """Log debug message if debug mode is enabled"""
        if self.LOG_DEBUG:
            try:
                print(self.clean_surrogates(msg))
            except Exception:
                pass
    
    def get_active_accounts(self, nombre_nora: Optional[str] = None) -> List[Dict]:
        """
        Obtiene cuentas activas de Meta Ads desde Supabase
        """
        query = self.supabase.table('meta_ads_cuentas').select(
            'id_cuenta_publicitaria, nombre_cliente, nombre_nora, estado_actual'
        )
        
        if nombre_nora:
            query = query.eq('nombre_nora', nombre_nora)
        
        # Excluir cuentas marcadas como excluidas
        query = query.neq('estado_actual', 'excluida')
        
        result = query.execute()
        return result.data or []
    
    def paginate_insights(self, url: str, params: Optional[Dict] = None, timeout: int = 30) -> List[Dict]:
        """
        Pagina a través de todas las páginas de insights de Meta API
        """
        all_insights = []
        current_url = url
        current_params = params
        page_num = 1
        
        while True:
            try:
                self._debug(f"📊 Obteniendo página {page_num} de insights...")
                response = requests.get(current_url, params=current_params, timeout=timeout)
                response.raise_for_status()
                
                data = response.json()
                page_insights = data.get('data', [])
                all_insights.extend(page_insights)
                
                print(f"   ✅ Página {page_num}: {len(page_insights)} insights (Total: {len(all_insights)})")
                
                # Verificar si hay siguiente página
                next_url = (data.get('paging') or {}).get('next')
                if not next_url:
                    break
                
                # Para siguientes páginas, usar la URL completa
                current_url = next_url
                current_params = None  # URL next ya incluye parámetros
                page_num += 1
                
                # Backoff para evitar rate limits
                time.sleep(0.4)
                
            except Exception as e:
                print(f"❌ Error en paginación: {self.clean_surrogates(str(e))}")
                break
        
        return all_insights
    
    def derive_messages_from_actions(self, actions: List[Dict]) -> int:
        """Deriva total de mensajes desde actions cuando no viene messaging_conversations_started"""
        total = 0.0
        for action in (actions or []):
            action_type = (action.get("action_type") or "").strip()
            if action_type in self.MSG_TYPES:
                try:
                    total += float(action.get("value", 0))
                except (TypeError, ValueError):
                    pass
        return int(total)
    
    def extract_all_metrics_from_actions(self, actions: List[Dict]) -> Dict:
        """Extrae TODAS las métricas posibles desde el array de actions"""
        metrics = {
            'link_clicks': 0,
            'page_engagement': 0,
            'post_engagement': 0,
            'video_views': 0,
            'post_reactions': 0,
            'post_likes': 0,
            'post_comments': 0,
            'post_shares': 0,
            'landing_page_views': 0,
            'page_likes': 0,
            'video_plays_3s': 0,
            'video_plays_15s': 0,
            'outbound_clicks': 0,
        }
        
        for action in (actions or []):
            action_type = (action.get("action_type") or "").strip()
            try:
                value = int(float(action.get("value", 0)))
            except (TypeError, ValueError):
                value = 0
            
            # Link clicks
            if action_type in ['link_click', 'onsite_conversion.link_click']:
                metrics['link_clicks'] += value
            
            # Page engagement
            elif action_type in ['page_engagement', 'onsite_conversion.page_engagement']:
                metrics['page_engagement'] += value
            
            # Post engagement
            elif action_type in ['post_engagement', 'onsite_conversion.post_engagement']:
                metrics['post_engagement'] += value
            
            # Video views
            elif action_type in ['video_view', 'onsite_conversion.video_view']:
                metrics['video_views'] += value
            
            # Post reactions
            elif action_type in ['post_reaction', 'onsite_conversion.post_reaction', 'onsite_conversion.post_net_like']:
                metrics['post_reactions'] += value
                if 'like' in action_type.lower():
                    metrics['post_likes'] += value
            
            # Comments
            elif action_type in ['comment', 'onsite_conversion.comment']:
                metrics['post_comments'] += value
            
            # Shares
            elif action_type in ['post', 'onsite_conversion.post']:
                metrics['post_shares'] += value
            
            # Landing page views
            elif action_type in ['landing_page_view', 'omni_landing_page_view', 'onsite_conversion.landing_page_view']:
                metrics['landing_page_views'] += value
            
            # Page likes
            elif action_type in ['like', 'page_like', 'onsite_conversion.page_like']:
                metrics['page_likes'] += value
            
            # Outbound clicks
            elif action_type in ['outbound_click', 'onsite_conversion.outbound_click']:
                metrics['outbound_clicks'] += value
        
        return metrics
    
    def compute_messaging_metrics(self, insight: Dict, sdk_data: Optional[Dict], actions: List[Dict], spend: float) -> Dict:
        """Unifica KPIs de mensajería con prioridad: SDK > insight > derivado de actions"""
        def _to_int(x):
            try:
                return int(float(x) if x is not None else 0)
            except Exception:
                return 0
        
        def _to_float(x):
            try:
                return float(x) if x is not None else None
            except Exception:
                return None
        
        out = {
            "messaging_conversations_started": 0,
            "messaging_first_reply": 0,
            "cost_per_message": None,
            "cost_per_messaging_first_reply": None,
            "cost_per_messaging_conversation_started": None,
            "mensajes_total": 0,
            "costo_por_mensaje_total": None,
            "msg_cost_is_calculated": False,
            "messages_source": "derived",
        }
        
        # 1) Insight directo (oficial de Meta)
        if insight:
            mcs = _to_int(insight.get("messaging_conversations_started"))
            if mcs > 0:
                out["messaging_conversations_started"] = mcs
                out["messages_source"] = "insight"
            
            cpmcs = _to_float(insight.get("cost_per_messaging_conversation_started"))
            if cpmcs is not None:
                out["cost_per_messaging_conversation_started"] = cpmcs
        
        # 2) Derivado de actions (fallback)
        if actions:
            derived_messages = self.derive_messages_from_actions(actions)
            if derived_messages > out["messaging_conversations_started"]:
                out["messaging_conversations_started"] = derived_messages
                if out["messages_source"] == "derived":
                    out["messages_source"] = "derived"
        
        # 3) Calcular mensajes totales y costos
        out["mensajes_total"] = out["messaging_conversations_started"] + out["messaging_first_reply"]
        
        if out["mensajes_total"] > 0 and spend > 0:
            out["costo_por_mensaje_total"] = spend / out["mensajes_total"]
            out["msg_cost_is_calculated"] = True
        
        return out
    
    def process_insight_to_daily_row(
        self,
        insight: Dict,
        account_id: str,
        fecha_reporte: date,
        nombre_nora: Optional[str] = None
    ) -> Dict:
        """
        Procesa un insight de Meta API y lo convierte en un registro diario para la BD
        
        Args:
            insight: Insight de la API
            account_id: ID de la cuenta publicitaria
            fecha_reporte: Fecha específica del reporte
            nombre_nora: Nombre de Nora (tenant)
            
        Returns:
            Dict con datos listos para insertar en meta_ads_anuncios_daily
        """
        # Obtener ad_id
        ad_id = insight.get('ad_id') or insight.get('id')
        if not ad_id:
            self._debug(f"⚠️ Insight sin ad_id, saltando...")
            return None
        
        # Platform
        platform = insight.get('publisher_platform') or 'facebook'
        
        # Helper para convertir a int seguro
        def safe_int(value):
            if value is None:
                return 0
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return 0
            if isinstance(value, list):
                return sum(int(float(item.get('value', 0))) for item in value if isinstance(item, dict))
            return 0
        
        # Helper para convertir a float seguro
        def safe_float(value):
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None
        
        # Procesar messaging metrics
        actions = insight.get('actions', [])
        messaging_metrics = self.compute_messaging_metrics(insight, None, actions, safe_float(insight.get('spend', 0)))
        
        # Extraer TODAS las métricas desde actions
        action_metrics = self.extract_all_metrics_from_actions(actions)
        
        # Calcular link_clicks: preferir de actions si no viene en insight
        link_clicks_value = safe_int(insight.get('link_clicks', 0))
        if link_clicks_value == 0 and action_metrics['link_clicks'] > 0:
            link_clicks_value = action_metrics['link_clicks']
        
        # Calcular interacciones totales (suma de engagements)
        interacciones = action_metrics['page_engagement'] + action_metrics['post_engagement']
        
        # Construir row de datos diarios con TODOS los campos posibles
        data = {
            # Identificadores
            'ad_id': str(ad_id),
            'id_cuenta_publicitaria': account_id,
            'campana_id': insight.get('campaign_id'),
            'conjunto_id': insight.get('adset_id'),
            
            # Nombres
            'nombre_anuncio': insight.get('ad_name'),
            'nombre_campana': insight.get('campaign_name'),
            'nombre_conjunto': insight.get('adset_name'),
            
            # Fechas - específicas para datos diarios
            'fecha_reporte': fecha_reporte.isoformat(),
            'fecha_desde': insight.get('date_start'),
            'fecha_hasta': insight.get('date_stop'),
            'fecha_sincronizacion': datetime.utcnow().isoformat(),
            'fecha_ultima_actualizacion': datetime.utcnow().isoformat(),
            
            # Platform y tenant
            'publisher_platform': platform,
            'nombre_nora': nombre_nora or '',
            'activo': True,
            
            # Métricas core
            'importe_gastado': safe_float(insight.get('spend', 0)),
            'impresiones': safe_int(insight.get('impressions', 0)),
            'alcance': safe_int(insight.get('reach', 0)),
            'clicks': safe_int(insight.get('clicks', 0)),
            'link_clicks': link_clicks_value,
            'inline_link_clicks': safe_int(insight.get('inline_link_clicks', 0)),
            'interacciones': interacciones,
            
            # Métricas de ratio
            'ctr': safe_float(insight.get('ctr')),
            'cpc': safe_float(insight.get('cpc')),
            'cost_per_1k_impressions': safe_float(insight.get('cpm')),
            'frequency': safe_float(insight.get('frequency')),
            
            # Métricas unique
            'unique_clicks': safe_int(insight.get('unique_clicks', 0)),
            'unique_inline_link_clicks': safe_int(insight.get('unique_inline_link_clicks', 0)),
            'unique_impressions': safe_int(insight.get('unique_impressions', 0)),
            'unique_ctr': safe_float(insight.get('unique_ctr')),
            
            # Outbound clicks
            'outbound_clicks': safe_int(insight.get('outbound_clicks', 0)) or action_metrics['outbound_clicks'],
            'outbound_clicks_ctr': safe_float(insight.get('outbound_clicks_ctr')),
            
            # Website
            'website_ctr': safe_float(insight.get('website_ctr')),
            
            # Engagement metrics desde actions
            'page_engagement': action_metrics['page_engagement'],
            'post_engagement': action_metrics['post_engagement'],
            'post_reactions': action_metrics['post_reactions'],
            'post_likes': action_metrics['post_likes'],
            'post_comments': action_metrics['post_comments'],
            'post_shares': action_metrics['post_shares'],
            'page_likes': action_metrics['page_likes'],
            
            # Video metrics desde actions
            'video_views': action_metrics['video_views'],
            'reproducciones_video_3s': action_metrics['video_plays_3s'],
            
            # Landing pages
            'landing_page_views': action_metrics['landing_page_views'],
            
            # Messaging metrics
            'messaging_conversations_started': messaging_metrics.get('messaging_conversations_started', 0),
            'messaging_first_reply': messaging_metrics.get('messaging_first_reply', 0),
            'mensajes_total': messaging_metrics.get('mensajes_total', 0),
            'cost_per_messaging_conversation_started': messaging_metrics.get('cost_per_messaging_conversation_started'),
            'cost_per_message': messaging_metrics.get('cost_per_message'),
            'cost_per_messaging_first_reply': messaging_metrics.get('cost_per_messaging_first_reply'),
            'costo_por_mensaje_total': messaging_metrics.get('costo_por_mensaje_total'),
            'msg_cost_is_calculated': messaging_metrics.get('msg_cost_is_calculated', False),
            'messages_source': messaging_metrics.get('messages_source'),
            
            # === CAMPOS ADICIONALES ===
            # Video avanzado (de actions)
            'video_30_sec_watched': safe_int(insight.get('video_30_sec_watched_actions', [])),
            'video_p25_watched': safe_int(insight.get('video_p25_watched_actions', [])),
            'video_p50_watched': safe_int(insight.get('video_p50_watched_actions', [])),
            'video_p75_watched': safe_int(insight.get('video_p75_watched_actions', [])),
            'video_p100_watched': safe_int(insight.get('video_p100_watched_actions', [])),
            'video_avg_time_watched': safe_float(insight.get('video_avg_time_watched_actions')),
            'video_play_actions_data': insight.get('video_play_actions'),
            
            # Conversiones
            'conversions_data': insight.get('conversions'),
            'conversion_values_data': insight.get('conversion_values'),
            'website_purchase_roas_value': safe_float(insight.get('website_purchase_roas')),
            'purchase_roas_value': safe_float(insight.get('purchase_roas')),
            
            # Cost per metrics directos
            'cost_per_inline_link_click_value': safe_float(insight.get('cost_per_inline_link_click')),
            'cost_per_unique_click_value': safe_float(insight.get('cost_per_unique_click')),
            'cost_per_unique_inline_link_click_value': safe_float(insight.get('cost_per_unique_inline_link_click')),
            'cost_per_unique_link_click_value': safe_float(insight.get('cost_per_unique_link_click')),
            
            # CTR adicionales
            'inline_link_click_ctr_value': safe_float(insight.get('inline_link_click_ctr')),
            'unique_link_clicks_ctr_value': safe_float(insight.get('unique_link_clicks_ctr')),
            
            # Estimated ad recall
            'estimated_ad_recallers_count': safe_int(insight.get('estimated_ad_recallers', 0)),
            'estimated_ad_recall_rate_value': safe_float(insight.get('estimated_ad_recall_rate')),
            
            # Thruplay
            'thruplays_count': safe_int(insight.get('video_thruplay_watched_actions', [])),
            'cost_per_thruplay_value': safe_float(insight.get('cost_per_thruplay')),
            
            # Cost per actions (JSONB - guardar completo)
            'cost_per_action_type_data': insight.get('cost_per_action_type'),
            'cost_per_conversion_data': insight.get('cost_per_conversion'),
            'cost_per_outbound_click_data': insight.get('cost_per_outbound_click'),
            'cost_per_unique_outbound_click_data': insight.get('cost_per_unique_outbound_click'),
            
            # Actions JSON (para debugging)
            'actions': actions if actions else None
        }
        
        return data
    
    def sync_account_daily(
        self,
        account_id: str,
        fecha_reporte: date,
        nombre_nora: Optional[str] = None
    ) -> Dict:
        """
        Sincroniza insights diarios de una cuenta de Meta Ads
        
        Args:
            account_id: ID de la cuenta publicitaria
            fecha_reporte: Fecha específica a sincronizar
            nombre_nora: Nombre de Nora (tenant)
            
        Returns:
            Dict con resultados de la sincronización
        """
        print(f"🔄 Sincronizando cuenta diaria: {self.clean_surrogates(str(account_id))} - {fecha_reporte}")
        
        # Normalizar account ID
        base_account_id = self.normalize_account_id(account_id)
        
        # Construir URL y parámetros EXACTAMENTE COMO NORA
        url = f"{self.BASE_URL}/act_{base_account_id}/insights"
        params = {
            'access_token': self.access_token,
            'level': 'ad',
            'breakdowns': 'publisher_platform',
            'action_breakdowns': 'action_type',
            'time_range': json.dumps({
                'since': fecha_reporte.strftime('%Y-%m-%d'),
                'until': fecha_reporte.strftime('%Y-%m-%d')
            }),
            'fields': ','.join(self.INSIGHT_FIELDS),
            'limit': 500,
        }
        
        print(f"📊 Obteniendo insights para fecha: {fecha_reporte}")
        
        try:
            # Obtener insights (paginado)
            all_insights = self.paginate_insights(url, params)
            
            if not all_insights:
                print(f"ℹ️ No se encontraron insights para cuenta {account_id} en fecha {fecha_reporte}")
                return {'ok': True, 'processed': 0, 'account_id': account_id, 'fecha': fecha_reporte.isoformat()}
            
            print(f"📊 Total insights obtenidos: {len(all_insights)}")
            
            # Marcar registros existentes como inactivos para esta fecha
            fecha_sync = datetime.utcnow().isoformat()
            self.supabase.table('meta_ads_anuncios_daily') \
                .update({'activo': False, 'fecha_ultima_actualizacion': fecha_sync}) \
                .eq('id_cuenta_publicitaria', account_id) \
                .eq('fecha_reporte', fecha_reporte.isoformat()) \
                .execute()
            
            # Procesar y upsert cada insight
            processed = 0
            errors = []
            
            for idx, insight in enumerate(all_insights):
                if (idx + 1) % self.LOG_EVERY == 0:
                    print(f"   Procesando {idx + 1}/{len(all_insights)}...")
                
                try:
                    row = self.process_insight_to_daily_row(
                        insight, account_id, fecha_reporte, nombre_nora
                    )
                    
                    if not row:
                        continue
                    
                    # Upsert a base de datos diaria
                    self.supabase.table('meta_ads_anuncios_daily') \
                        .upsert(
                            row,
                            on_conflict='ad_id,fecha_reporte,publisher_platform'
                        ) \
                        .execute()
                    
                    processed += 1
                    
                except Exception as e:
                    error_msg = f"Error procesando ad {insight.get('ad_id')}: {str(e)}"
                    errors.append(error_msg)
                    self._debug(error_msg)
            
            print(f"✅ Sincronización diaria completa: {processed} anuncios procesados")
            
            return {
                'ok': True,
                'processed': processed,
                'errors': errors,
                'account_id': account_id,
                'fecha': fecha_reporte.isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando cuenta {account_id} en fecha {fecha_reporte}: {str(e)}"
            print(f"❌ {error_msg}")
            return {'ok': False, 'error': error_msg, 'account_id': account_id, 'fecha': fecha_reporte.isoformat()}
    
    def sync_all_accounts_daily(
        self,
        fecha_reporte: date,
        nombre_nora: Optional[str] = None
    ) -> Dict:
        """
        Sincroniza todas las cuentas activas para una fecha específica
        
        Args:
            fecha_reporte: Fecha específica a sincronizar
            nombre_nora: Filtrar por nombre de Nora (opcional)
            
        Returns:
            Dict con resultados de la sincronización
        """
        print(f"🗓️ Sincronización diaria para fecha: {fecha_reporte}")
        
        # Obtener cuentas activas
        accounts = self.get_active_accounts(nombre_nora)
        
        if not accounts:
            return {'ok': False, 'error': 'No se encontraron cuentas activas'}
        
        print(f"📊 Cuentas a sincronizar: {len(accounts)}")
        for cuenta in accounts:
            nombre_cliente = self.clean_surrogates(cuenta.get('nombre_cliente', 'Sin nombre'))
            estado = cuenta.get('estado_actual', 'NULL')
            print(f"   • {nombre_cliente} ({cuenta['id_cuenta_publicitaria']}) - Estado: {estado}")
        
        # Resultados
        resultados = {
            'ok': True,
            'cuentas_procesadas': 0,
            'cuentas_exitosas': 0,
            'errores': [],
            'cuentas_con_errores': [],
            'fecha_reporte': fecha_reporte.isoformat()
        }
        
        # Procesar cada cuenta
        for cuenta in accounts:
            cuenta_id = cuenta['id_cuenta_publicitaria']
            nombre_cliente = self.clean_surrogates(cuenta.get('nombre_cliente', 'Cliente desconocido'))
            
            try:
                print(f"\n============================================================")
                print(f"📊 Procesando: {nombre_cliente}")
                print(f"============================================================")
                
                result = self.sync_account_daily(
                    account_id=cuenta_id,
                    fecha_reporte=fecha_reporte,
                    nombre_nora=cuenta.get('nombre_nora')
                )
                
                if result.get('ok'):
                    resultados['cuentas_exitosas'] += 1
                    print(f"✅ Exitosa: {nombre_cliente}")
                else:
                    error_info = {
                        'cuenta_id': cuenta_id,
                        'nombre_cliente': nombre_cliente,
                        'error': result.get('error', 'Error desconocido')
                    }
                    resultados['errores'].append(f"Falló cuenta {cuenta_id} ({nombre_cliente})")
                    resultados['cuentas_con_errores'].append(error_info)
                    print(f"❌ Falló: {nombre_cliente}")
                
            except Exception as e:
                error_info = {
                    'cuenta_id': cuenta_id,
                    'nombre_cliente': nombre_cliente,
                    'error': str(e)
                }
                resultados['errores'].append(f"Error en cuenta {cuenta_id} ({nombre_cliente}): {str(e)}")
                resultados['cuentas_con_errores'].append(error_info)
                print(f"💥 Error en {nombre_cliente}: {self.clean_surrogates(str(e))}")
            
            resultados['cuentas_procesadas'] += 1
        
        # Resumen final
        self._print_summary(resultados)
        
        return resultados
    
    def _print_summary(self, resultados: Dict) -> None:
        """Imprime resumen final de la sincronización"""
        print("\n" + "="*80)
        print("📊 RESUMEN DE SINCRONIZACIÓN DIARIA META ADS")
        print("="*80)
        print(f"🗓️ Fecha: {resultados['fecha_reporte']}")
        print(f"📈 Cuentas procesadas: {resultados['cuentas_procesadas']}")
        print(f"✅ Cuentas exitosas: {resultados['cuentas_exitosas']}")
        print(f"❌ Cuentas con errores: {len(resultados['cuentas_con_errores'])}")
        
        if resultados['cuentas_con_errores']:
            print("\n🚨 DETALLE DE ERRORES:")
            print("-" * 50)
            for i, error_info in enumerate(resultados['cuentas_con_errores'], 1):
                print(f"{i}. {error_info['nombre_cliente']} ({error_info['cuenta_id']})")
                print(f"   Error: {self.clean_surrogates(str(error_info['error']))}")
                print()
        else:
            print("\n🎉 ¡Todas las cuentas se sincronizaron correctamente!")
        
        print("="*80)