"""
Meta Ads Sync Service

Sincroniza datos diarios de anuncios de Meta (Facebook/Instagram) desde la API de Meta
a la tabla meta_ads_anuncios_detalle en Supabase.

Características:
- Paginación automática de insights
- Procesamiento de métricas de messaging (conversaciones, first replies, costos)
- Caché de nombres de campañas/adsets
- Multi-tenant via nombre_nora
- Soporte para SDK y HTTP fallback
"""

import os
import json
import time
import requests
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from dotenv import load_dotenv

from ...db.supabase_client import create_client_from_env

# Load environment variables
load_dotenv()


class MetaAdsSyncService:
    """Servicio para sincronizar datos de Meta Ads a Supabase"""
    
    # API Configuration
    GRAPH_API_VERSION = os.getenv('META_API_VERSION', 'v23.0')
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    
    # Cache configuration
    NAME_CACHE_TTL = int(os.getenv('NAMES_CACHE_TTL', '3600'))
    _name_cache = {}
    
    # Debug configuration
    LOG_DEBUG = os.getenv("META_SYNC_DEBUG", "0") == "1"
    LOG_EVERY = int(os.getenv("META_SYNC_LOG_EVERY", "100") or "100")
    
    # Fields básicos probados que funcionan
    INSIGHT_FIELDS = [
        # Identificadores y fechas básicos
        "ad_id", "date_start", "date_stop", "account_id", "campaign_id", "adset_id",
        # Métricas básicas probadas
        "impressions", "clicks", "spend",
        # Actions para derivar messaging
        "actions"
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
        
        Args:
            nombre_nora: Filtrar por nombre_nora específico (opcional)
            
        Returns:
            Lista de diccionarios con información de cuentas
        """
        query = self.supabase.table('meta_ads_cuentas') \
            .select('id_cuenta_publicitaria, nombre_cliente, nombre_nora, estado_actual')
        
        if nombre_nora:
            query = query.eq('nombre_nora', nombre_nora)
        
        # Excluir cuentas marcadas como 'excluida'
        query = query.neq('estado_actual', 'excluida')
        
        response = query.execute()
        return response.data or []
    
    def paginate_insights(self, url: str, params: Optional[Dict] = None, timeout: int = 30) -> List[Dict]:
        """
        Pagina a través de todas las páginas de insights de Meta API
        
        Args:
            url: URL inicial de la API
            params: Parámetros de la petición (opcional para siguientes páginas)
            timeout: Timeout de la petición en segundos
            
        Returns:
            Lista de todos los insights obtenidos
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
    
    def get_ad_names_cached(self, ad_id: str) -> Dict[str, Optional[str]]:
        """
        Obtiene nombres de campaña/adset con caché TTL
        
        Args:
            ad_id: ID del anuncio
            
        Returns:
            Dict con campaign_name, adset_name, ad_name, status
        """
        if not ad_id:
            return {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}
        
        # Check cache
        now_ts = time.time()
        if ad_id in self._name_cache:
            expires, payload = self._name_cache[ad_id]
            if expires > now_ts:
                self._debug(f"✨ Cache hit para ad {ad_id}")
                return payload
        
        # Cache miss: fetch from API
        try:
            url = f"{self.BASE_URL}/{ad_id}"
            params = {
                'access_token': self.access_token,
                'fields': 'name,status,campaign{name,status},adset{name,status}'
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                campaign = data.get('campaign', {})
                adset = data.get('adset', {})
                
                payload = {
                    "campaign_name": campaign.get('name'),
                    "campaign_status": campaign.get('status'),
                    "adset_name": adset.get('name'),
                    "adset_status": adset.get('status'),
                    "ad_name": data.get('name'),
                    "status": data.get('status')
                }
                
                # Save to cache
                self._name_cache[ad_id] = (now_ts + self.NAME_CACHE_TTL, payload)
                return payload
            else:
                self._debug(f"⚠️ Meta API error {response.status_code} for ad {ad_id}")
        except Exception as e:
            self._debug(f"⚠️ Error fetching names for ad {ad_id}: {e}")
        
        # Fallback
        return {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}
    
    def derive_messages_from_actions(self, actions: List[Dict]) -> int:
        """
        Deriva total de mensajes desde actions cuando no viene messaging_conversations_started
        
        Args:
            actions: Lista de actions del insight
            
        Returns:
            Total de mensajes derivados
        """
        total = 0.0
        for action in (actions or []):
            action_type = (action.get("action_type") or "").strip()
            if action_type in self.MSG_TYPES:
                try:
                    total += float(action.get("value", 0))
                except (TypeError, ValueError):
                    pass
        return int(total)
    
    def compute_messaging_metrics(
        self,
        insight: Dict,
        sdk_data: Optional[Dict],
        actions: List[Dict],
        spend: float
    ) -> Dict:
        """
        Unifica KPIs de mensajería con prioridad: SDK > insight > derivado de actions
        
        Args:
            insight: Insight de la API de Meta
            sdk_data: Datos del SDK (opcional)
            actions: Lista de actions
            spend: Importe gastado
            
        Returns:
            Dict con métricas de messaging unificadas
        """
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
        
        # 1) SDK primero (prioridad más alta)
        if sdk_data:
            ms = _to_int(sdk_data.get("messages_started"))
            fr = _to_int(sdk_data.get("first_replies"))
            out["messaging_conversations_started"] = max(out["messaging_conversations_started"], ms)
            out["messaging_first_reply"] = max(out["messaging_first_reply"], fr)
            out["cost_per_message"] = _to_float(
                sdk_data.get("cost_per_message") or sdk_data.get("cost_per_1_message")
            )
            cfr = _to_float(sdk_data.get("cost_per_messaging_first_reply"))
            if cfr is not None:
                out["cost_per_messaging_first_reply"] = cfr
            out["messages_source"] = "sdk"
        
        # 2) Insight directo (oficial de Meta)
        if insight:
            mcs = _to_int(insight.get("messaging_conversations_started"))
            if mcs > out["messaging_conversations_started"]:
                out["messaging_conversations_started"] = mcs
                out["messages_source"] = "insight"
            
            cpmcs = _to_float(insight.get("cost_per_messaging_conversation_started"))
            if cpmcs is not None:
                out["cost_per_messaging_conversation_started"] = cpmcs
        
        # 3) Derivado de actions (fallback)
        if actions:
            derived_messages = self.derive_messages_from_actions(actions)
            if derived_messages > out["messaging_conversations_started"] and out["messages_source"] == "derived":
                out["messaging_conversations_started"] = derived_messages
            
            # Procesar first replies
            first = 0
            FIRST_REPLY_ACTIONS = {
                "messaging_first_reply", "first_reply",
                "onsite_conversion.messaging_first_reply",
                "onsite_conversion.messaging_conversation_replied_7d"
            }
            for a in actions:
                if a.get("action_type") in FIRST_REPLY_ACTIONS:
                    try:
                        first += int(float(a.get("value", 0)))
                    except (TypeError, ValueError):
                        pass
            
            if first > out["messaging_first_reply"] and out["messages_source"] == "derived":
                out["messaging_first_reply"] = first
        
        # 4) Calcular mensajes totales y costos
        out["mensajes_total"] = (out["messaging_conversations_started"] or 0) + (out["messaging_first_reply"] or 0)
        
        if (out["mensajes_total"] or 0) > 0:
            c = _to_float(spend)
            if c is not None and c > 0:
                out["costo_por_mensaje_total"] = c / out["mensajes_total"]
                out["msg_cost_is_calculated"] = True
        
        return out
    
    def process_insight_to_db_row(
        self,
        insight: Dict,
        account_id: str,
        fecha_inicio: date,
        fecha_fin: date,
        nombre_nora: Optional[str] = None
    ) -> Dict:
        """
        Procesa un insight de Meta API y lo convierte en un registro para la BD
        
        Args:
            insight: Insight de la API
            account_id: ID de la cuenta publicitaria
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de fin
            nombre_nora: Nombre de Nora (tenant)
            
        Returns:
            Dict con datos listos para insertar en meta_ads_anuncios_detalle
        """
        # Obtener ad_id (puede venir como 'ad_id' o 'id')
        ad_id = insight.get('ad_id') or insight.get('id')
        if not ad_id:
            self._debug(f"⚠️ Insight sin ad_id, saltando...")
            return None
        
        # Obtener nombres desde cache
        names = self.get_ad_names_cached(str(ad_id))
        
        # Platform
        platform = insight.get('publisher_platform') or 'facebook'
        
        # Compute messaging metrics
        spend = float(insight.get('spend', 0) or 0.0)
        actions = insight.get('actions', [])
        metrics = self.compute_messaging_metrics(insight, None, actions, spend)
        
        # Helper para convertir a int seguro
        def safe_int(value):
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, list):
                return sum(int(float(item.get('value', 0))) for item in value if isinstance(item, dict))
            return 0
        
        # Helper para convertir a float seguro
        def safe_float(value):
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None
        
        # Construir row de datos
        data = {
            # Identificadores
            'ad_id': str(ad_id),
            'id_cuenta_publicitaria': account_id,
            'campana_id': str(insight.get('campaign_id') or ''),
            'conjunto_id': str(insight.get('adset_id') or ''),
            
            # Nombres
            'nombre_anuncio': (
                insight.get('ad_name') or
                names.get('ad_name') or
                str(ad_id)
            ),
            'nombre_campana': (
                insight.get('campaign_name') or
                names.get('campaign_name')
            ),
            'nombre_conjunto': (
                insight.get('adset_name') or
                names.get('adset_name')
            ),
            
            # Objetivo y status
            'objetivo_campana': insight.get('objective'),
            'status': names.get('status'),
            'status_campana': (
                insight.get('campaign_status') or
                insight.get('campaign_effective_status') or
                names.get('campaign_status')
            ),
            'status_conjunto': (
                insight.get('adset_status') or
                insight.get('adset_effective_status') or
                names.get('adset_status')
            ),
            
            # Fechas - específicas para daily
            'fecha_reporte': fecha_inicio.isoformat(),  # Para daily usamos fecha_inicio como fecha_reporte
            'fecha_desde': insight.get('date_start') or fecha_inicio.isoformat(),
            'fecha_hasta': insight.get('date_stop') or fecha_fin.isoformat(),
            'fecha_sincronizacion': datetime.utcnow().isoformat(),
            'fecha_ultima_actualizacion': datetime.utcnow().isoformat(),
            
            # Platform y tenant
            'publisher_platform': platform,
            'nombre_nora': nombre_nora or '',
            'activo': True,
            
            # Métricas core
            'importe_gastado': spend,
            'impresiones': safe_int(insight.get('impressions', 0)),
            'alcance': safe_int(insight.get('reach', 0)),
            'clicks': safe_int(insight.get('clicks', 0)),
            'link_clicks': safe_int(insight.get('link_clicks', 0)),
            'inline_link_clicks': safe_int(insight.get('inline_link_clicks', 0)),
            'frequency': safe_float(insight.get('frequency', 0)),
            'ctr': safe_float(insight.get('ctr', 0)),
            'cpc': safe_float(insight.get('cpc', 0)),
            'cost_per_1k_impressions': safe_float(insight.get('cpm', 0)),
            
            # Métricas unique
            'unique_impressions': safe_int(insight.get('reach', 0)),
            'unique_clicks': safe_int(insight.get('clicks', 0)),
            'unique_inline_link_clicks': safe_int(insight.get('inline_link_clicks', 0)),
            'unique_ctr': safe_float(insight.get('ctr', 0)),
            
            # Métricas de messaging
            'messaging_conversations_started': metrics.get('messaging_conversations_started', 0),
            'messaging_first_reply': metrics.get('messaging_first_reply', 0),
            'mensajes_total': metrics.get('mensajes_total', 0),
            'cost_per_message': metrics.get('cost_per_message'),
            'cost_per_messaging_first_reply': metrics.get('cost_per_messaging_first_reply'),
            'cost_per_messaging_conversation_started': metrics.get('cost_per_messaging_conversation_started'),
            'costo_por_mensaje_total': metrics.get('costo_por_mensaje_total'),
            'msg_cost_is_calculated': metrics.get('msg_cost_is_calculated', False),
            'messages_source': metrics.get('messages_source'),
            
            # Métricas de video
            'video_plays': safe_int(insight.get('video_plays', 0)),
            'thruplays': safe_int(insight.get('thruplays', 0)),
            'video_plays_at_25': safe_int(insight.get('video_plays_at_25', 0)),
            'video_plays_at_50': safe_int(insight.get('video_plays_at_50', 0)),
            'video_plays_at_75': safe_int(insight.get('video_plays_at_75', 0)),
            'video_plays_at_100': safe_int(insight.get('video_plays_at_100', 0)),
            
            # Outbound
            'unique_outbound_clicks': safe_int(insight.get('outbound_clicks', 0)),
        }
        
        return data
    
    def sync_account(
        self,
        account_id: str,
        fecha_inicio: date,
        fecha_fin: date,
        nombre_nora: Optional[str] = None
    ) -> Dict:
        """
        Sincroniza insights de una cuenta de Meta Ads
        
        Args:
            account_id: ID de la cuenta publicitaria
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de fin
            nombre_nora: Nombre de Nora (tenant)
            
        Returns:
            Dict con resultados de la sincronización
        """
        print(f"🔄 Sincronizando cuenta: {self.clean_surrogates(str(account_id))}")
        
        # Normalizar account ID
        base_account_id = self.normalize_account_id(account_id)
        
        # Construir URL y parámetros (usando patrón del archivo original)
        url = f"{self.BASE_URL}/act_{base_account_id}/insights"
        params = {
            'access_token': self.access_token,
            'level': 'ad',
            'breakdowns': 'publisher_platform',
            'action_breakdowns': 'action_type',
            'time_range': json.dumps({
                'since': fecha_inicio.strftime('%Y-%m-%d'),
                'until': fecha_fin.strftime('%Y-%m-%d')
            }),
            'fields': ','.join(self.INSIGHT_FIELDS),
            'limit': 500,
        }
        
        print(f"📊 Obteniendo insights entre {fecha_inicio} y {fecha_fin}")
        
        try:
            # Obtener insights (paginado)
            all_insights = self.paginate_insights(url, params)
            
            if not all_insights:
                print(f"ℹ️ No se encontraron insights para cuenta {account_id}")
                return {'ok': True, 'processed': 0, 'account_id': account_id}
            
            print(f"📊 Total insights obtenidos: {len(all_insights)}")
            
            # Marcar registros existentes como inactivos
            fecha_sync = datetime.utcnow().isoformat()
            self.supabase.table('meta_ads_anuncios_daily') \
                .update({'activo': False, 'fecha_ultima_actualizacion': fecha_sync}) \
                .eq('id_cuenta_publicitaria', account_id) \
                .eq('fecha_reporte', fecha_inicio.isoformat()) \
                .execute()
            
            # Procesar y upsert cada insight
            processed = 0
            errors = []
            
            for idx, insight in enumerate(all_insights):
                if (idx + 1) % self.LOG_EVERY == 0:
                    print(f"   Procesando {idx + 1}/{len(all_insights)}...")
                
                try:
                    row = self.process_insight_to_db_row(
                        insight, account_id, fecha_inicio, fecha_fin, nombre_nora
                    )
                    
                    if not row:
                        continue
                    
                    # Upsert a base de datos
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
            
            print(f"✅ Sincronización completa: {processed} anuncios procesados")
            
            return {
                'ok': True,
                'processed': processed,
                'errors': errors,
                'account_id': account_id
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando cuenta {account_id}: {str(e)}"
            print(f"❌ {error_msg}")
            return {'ok': False, 'error': error_msg, 'account_id': account_id}
    
    def sync_all_accounts(
        self,
        nombre_nora: Optional[str] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None
    ) -> Dict:
        """
        Sincroniza todas las cuentas activas
        
        Args:
            nombre_nora: Filtrar por tenant específico (opcional)
            fecha_inicio: Fecha de inicio (default: hace 7 días)
            fecha_fin: Fecha de fin (default: ayer)
            
        Returns:
            Dict con resumen de la sincronización
        """
        hoy = date.today()
        
        if not fecha_fin:
            fecha_fin = hoy - timedelta(days=1)
        elif isinstance(fecha_fin, str):
            fecha_fin = date.fromisoformat(fecha_fin)
        
        if not fecha_inicio:
            fecha_inicio = fecha_fin - timedelta(days=7)
        elif isinstance(fecha_inicio, str):
            fecha_inicio = date.fromisoformat(fecha_inicio)
        
        print(f"🗓️ Fecha actual: {hoy}")
        print(f"🔄 Sincronizando período: {fecha_inicio} → {fecha_fin}")
        
        # Obtener cuentas activas
        cuentas = self.get_active_accounts(nombre_nora)
        
        if not cuentas:
            return {'ok': False, 'error': 'No se encontraron cuentas activas'}
        
        print(f"📊 Cuentas a sincronizar: {len(cuentas)}")
        for cuenta in cuentas:
            estado = cuenta.get('estado_actual', 'NULL')
            nombre_cliente = self.clean_surrogates(cuenta.get('nombre_cliente', 'Sin nombre'))
            print(f"   • {nombre_cliente} ({cuenta['id_cuenta_publicitaria']}) - Estado: {estado}")
        
        # Sincronizar cada cuenta
        results = {
            'ok': True,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'cuentas_procesadas': 0,
            'cuentas_exitosas': 0,
            'cuentas_con_errores': [],
            'total_ads_procesados': 0
        }
        
        for cuenta in cuentas:
            cuenta_id = cuenta['id_cuenta_publicitaria']
            nombre_cliente = self.clean_surrogates(cuenta.get('nombre_cliente', 'Cliente desconocido'))
            nora = cuenta.get('nombre_nora')
            
            print(f"\\n{'='*60}")
            print(f"📊 Procesando: {nombre_cliente}")
            print(f"{'='*60}")
            
            try:
                result = self.sync_account(
                    account_id=cuenta_id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    nombre_nora=nora
                )
                
                if result.get('ok'):
                    results['cuentas_exitosas'] += 1
                    results['total_ads_procesados'] += result.get('processed', 0)
                else:
                    results['cuentas_con_errores'].append({
                        'cuenta': nombre_cliente,
                        'cuenta_id': cuenta_id,
                        'error': result.get('error')
                    })
                    
            except Exception as e:
                error_msg = str(e)
                results['cuentas_con_errores'].append({
                    'cuenta': nombre_cliente,
                    'cuenta_id': cuenta_id,
                    'error': error_msg
                })
                print(f"❌ Error: {self.clean_surrogates(error_msg)}")
            
            results['cuentas_procesadas'] += 1
        
        # Resumen final
        print(f"\\n{'='*80}")
        print("📊 RESUMEN DE SINCRONIZACIÓN META ADS")
        print(f"{'='*80}")
        print(f"🗓️ Período: {fecha_inicio} → {fecha_fin}")
        print(f"📈 Cuentas procesadas: {results['cuentas_procesadas']}")
        print(f"✅ Cuentas exitosas: {results['cuentas_exitosas']}")
        print(f"📊 Total ads procesados: {results['total_ads_procesados']}")
        print(f"❌ Cuentas con errores: {len(results['cuentas_con_errores'])}")
        
        if results['cuentas_con_errores']:
            print(f"\\n🚨 DETALLE DE ERRORES:")
            print("-" * 50)
            for i, error_info in enumerate(results['cuentas_con_errores'], 1):
                print(f"{i}. {error_info['cuenta']} ({error_info['cuenta_id']})")
                print(f"   Error: {self.clean_surrogates(error_info['error'])}")
        else:
            print(f"\\n🎉 ¡Todas las cuentas se sincronizaron correctamente!")
        
        print(f"{'='*80}")
        
        return results
