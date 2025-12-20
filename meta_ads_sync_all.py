# Archivo: clientes/aura/tasks/meta_ads_sync_all.py
from clientes.aura.utils.supabase_client import supabase
import os
import requests
import json
import time
from datetime import datetime, date, timedelta

# 🗄️ CONTEXTO BD PARA GITHUB COPILOT
from clientes.aura.utils.supabase_schemas import SUPABASE_SCHEMAS
from clientes.aura.utils.quick_schemas import existe, columnas
from clientes.aura.utils.meta_insights_fields import load_fields
# 🔌 Util unificado de Meta/Facebook (lazy imports con degradación suave)
from clientes.aura.utils.fb_sdk import (
    GRAPH_API_VERSION,
    get_graph,
    init_business,
    insights_generic,
    insights_mensajes,  # ← KPIs de Mensajes normalizados
)
# BD ACTUAL: meta_ads_cuentas(15), meta_ads_anuncios_detalle(96), meta_ads_reportes_semanales(35)

# Función para limpiar caracteres surrogates
def clean_surrogates(text: str) -> str:
    """Limpia caracteres surrogates de una cadena para evitar errores de encoding UTF-8."""
    if not isinstance(text, str):
        return str(text)
    return text.encode('utf-8', errors='ignore').decode('utf-8')

# ---------------------------------------------------------------------
# Campos base de insight ampliados (se piden explícitamente)
# ---------------------------------------------------------------------
INSIGHT_FIELDS_BASE = [
    # claves y fechas
    "date_start","date_stop","account_id","campaign_id","adset_id","ad_id",
    # naming y objetivo (para llenar meta_ads_anuncios_detalle)
    "ad_name","adset_name","campaign_name","objective",
    # métricas core
    "impressions","reach","clicks","link_clicks","inline_link_clicks",
    "spend","cpm","cpc","ctr","unique_ctr",
    # messaging direct
    "messaging_conversations_started","cost_per_messaging_conversation_started",
    # acciones (fallback de mensajes)
    "actions","action_values",
    # video
    "video_p25_watched_actions","video_p50_watched_actions","video_p75_watched_actions","video_p100_watched_actions",
    "video_10_sec_watched_actions","video_15_sec_watched_actions","video_30_sec_watched_actions","video_avg_time_watched_actions",
    "video_plays","video_plays_at_25","video_plays_at_50","video_plays_at_75","video_plays_at_100",
    # ranking y uniques
    "quality_ranking","unique_clicks","unique_inline_link_clicks","unique_impressions",
    # outbound / thruplay / web
    "outbound_clicks","outbound_clicks_ctr","thruplay_rate","thruplays","website_ctr"
]


# ---------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------
_MSG_TYPES = {
    "onsite_conversion.messaging_conversation_started_7d",
    "onsite_conversion.messaging_conversation_started",  # Agregado: caso sin _7d
    "messaging_conversation_started_7d", 
    "messaging_conversation_started",                   # Agregado: caso simple
    "onsite_conversion.messaging_first_reply",
    "messaging_first_reply",                           # Agregado: caso simple
    "onsite_conversion.total_messaging_connection",
    "total_messaging_connection",                      # Agregado: caso simple
}

def _derive_messages_from_actions(insight: dict) -> int:
    """Si no viene messaging_conversations_started, sumar desde actions."""
    total = 0.0
    for a in (insight.get("actions") or []):
        t = (a.get("action_type") or "").strip()
        if t in _MSG_TYPES:
            try:
                total += float(a.get("value") or 0)
            except Exception:
                pass
    return int(total)


def sincronizar_todas_las_cuentas_meta_ads(nombre_nora=None, fecha_inicio=None, fecha_fin=None):
    hoy = date.today()
    print(f"🗓️ Fecha actual del sistema: {clean_surrogates(str(hoy))}")

    if not fecha_fin:
        fecha_fin = hoy - timedelta(days=1)
    elif isinstance(fecha_fin, str):
        fecha_fin = date.fromisoformat(fecha_fin)

    if not fecha_inicio:
        fecha_inicio = fecha_fin - timedelta(days=7)
    elif isinstance(fecha_inicio, str):
        fecha_inicio = date.fromisoformat(fecha_inicio)

    access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
    if not access_token:
        return {'ok': False, 'error': 'No se encontró el token META_ACCESS_REDACTED_TOKEN'}

    # Seleccionar todas las cuentas que no estén excluidas (incluye NULL, 'activa', 'pausada', etc.)
    query = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria, nombre_cliente, nombre_nora, estado_actual')
    if nombre_nora:
        query = query.eq('nombre_nora', nombre_nora)
    query = query.neq('estado_actual', 'excluida')  # Incluir NULL y cualquier valor distinto de 'excluida'

    cuentas = query.execute()
    if not cuentas.data:
        return {'ok': False, 'error': 'No se encontraron cuentas activas'}

    print(f"📊 Cuentas seleccionadas para sincronización: {len(cuentas.data)}")
    for cuenta in cuentas.data:
        estado = cuenta.get('estado_actual', 'NULL')
        # Limpiar caracteres problemáticos antes de imprimir
        nombre_cliente = cuenta.get('nombre_cliente', 'Sin nombre')
        if isinstance(nombre_cliente, str):
            nombre_cliente = nombre_cliente.encode('utf-8', errors='ignore').decode('utf-8')
        print(f"   • {clean_surrogates(nombre_cliente)} ({cuenta['id_cuenta_publicitaria']}) - Estado: {clean_surrogates(str(estado))}")

    resultados = {
        'ok': True,
        'cuentas_procesadas': 0,
        'cuentas_exitosas': 0,
        'errores': [],
        'cuentas_con_errores': [],
        'fecha_inicio': fecha_inicio.isoformat(),
        'fecha_fin': fecha_fin.isoformat()
    }

    for cuenta in cuentas.data:
        cuenta_id = cuenta['id_cuenta_publicitaria']
        nombre_cliente = cuenta.get('nombre_cliente', 'Cliente desconocido')
        # Limpiar surrogates del nombre del cliente
        if isinstance(nombre_cliente, str):
            nombre_cliente = nombre_cliente.encode('utf-8', errors='ignore').decode('utf-8')
        nombre_nora = cuenta.get('nombre_nora', 'Sin Nora')
        
        try:
            print(f"🔄 Procesando: {clean_surrogates(nombre_cliente)} ({cuenta_id})")
            exito = sincronizar_cuenta_meta_ads_simple(
                ad_account_id=cuenta_id,
                access_token=access_token,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                nombre_nora=cuenta.get('nombre_nora')
            )
            if exito:
                resultados['cuentas_exitosas'] += 1
                # nombre_cliente ya está limpio desde arriba
                print(f"✅ Exitosa: {clean_surrogates(nombre_cliente)}")
            else:
                error_info = {
                    'cuenta_id': cuenta_id,
                    'nombre_cliente': nombre_cliente,
                    'nombre_nora': nombre_nora,
                    'error': 'Falló la sincronización sin excepción'
                }
                resultados['errores'].append(f"Falló cuenta {cuenta_id} ({nombre_cliente})")
                resultados['cuentas_con_errores'].append(error_info)
                # nombre_cliente ya está limpio desde arriba
                print(f"❌ Falló: {clean_surrogates(nombre_cliente)}")
        except Exception as e:
            error_info = {
                'cuenta_id': cuenta_id,
                'nombre_cliente': nombre_cliente,
                'nombre_nora': nombre_nora,
                'error': str(e)
            }
            resultados['errores'].append(f"Error en cuenta {cuenta_id} ({nombre_cliente}): {str(e)}")
            resultados['cuentas_con_errores'].append(error_info)
            # nombre_cliente ya está limpio desde arriba
            print(f"💥 Error en {clean_surrogates(nombre_cliente)}: {clean_surrogates(str(e))}")

        resultados['cuentas_procesadas'] += 1

    # Generar resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DE SINCRONIZACIÓN META ADS")
    print("="*80)
    print(f"🗓️ Período: {clean_surrogates(str(fecha_inicio))} → {clean_surrogates(str(fecha_fin))}")
    print(f"📈 Cuentas procesadas: {resultados['cuentas_procesadas']}")
    print(f"✅ Cuentas exitosas: {resultados['cuentas_exitosas']}")
    print(f"❌ Cuentas con errores: {len(resultados['cuentas_con_errores'])}")
    
    if resultados['cuentas_con_errores']:
        print("\n🚨 DETALLE DE ERRORES:")
        print("-" * 50)
        for i, error_info in enumerate(resultados['cuentas_con_errores'], 1):
            print(f"{i}. {clean_surrogates(error_info['nombre_cliente'])} ({error_info['cuenta_id']})")
            print(f"   Nora: {clean_surrogates(error_info['nombre_nora'])}")
            print(f"   Error: {clean_surrogates(str(error_info['error']))}")
            print()
    else:
        print("\n🎉 ¡Todas las cuentas se sincronizaron correctamente!")
    
    print("="*80)

    return resultados


# ---------------------------------------------------------------------
# Feature flags / allowed columns handling
# ---------------------------------------------------------------------
HAS_NEW_MSG_COLS = os.getenv("HAS_NEW_MSG_COLS", "0") == "1"

# Build ALLOWED_COLUMNS dynamically from SUPABASE_SCHEMAS but allow
# adding the new messaging/name columns when HAS_NEW_MSG_COLS=1
try:
    _schema_cols = set(SUPABASE_SCHEMAS.get('meta_ads_anuncios_detalle', {}).keys())
except Exception:
    _schema_cols = set()

# New columns requested by the feature (only written when HAS_NEW_MSG_COLS=True)
_NEW_MSG_COLUMNS = {
    'messaging_first_reply', 'mensajes_total', 'cost_per_message',
    'cost_per_messaging_first_reply', 'costo_por_mensaje_total', 'msg_cost_is_calculated',
    'nombre_campana', 'nombre_conjunto'
}

ALLOWED_COLUMNS = set(_schema_cols)
if HAS_NEW_MSG_COLS:
    ALLOWED_COLUMNS |= _NEW_MSG_COLUMNS


# In-memory lightweight cache for ad names to avoid rate limits
# Structure: { ad_id: (expires_ts, {"campaign_name":..., "adset_name":..., "ad_name":..., "status":...}) }
_NAME_CACHE = {}
_NAME_CACHE_TTL = int(os.getenv('NAMES_CACHE_TTL', '3600'))

def get_names_cached(ad_id: str, access_token: str):
    """Return a small dict with campaign_name and adset_name (and ad name/status) with TTL caching."""
    if not ad_id:
        return {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}
    now_ts = time.time()
    entry = _NAME_CACHE.get(ad_id)
    if entry:
        expires, payload = entry
        if expires > now_ts:
            return payload
    # Miss: fetch via obtener_info_anuncio (graceful)
    try:
        info = obtener_info_anuncio(ad_id, access_token) or {}
        payload = {
            "campaign_name": info.get('campaign_name'),
            "campaign_status": info.get('campaign_status'),
            "adset_name": info.get('adset_name'),
            "adset_status": info.get('adset_status'),
            "ad_name": info.get('name'),
            "status": info.get('status')
        }
        _NAME_CACHE[ad_id] = (now_ts + _NAME_CACHE_TTL, payload)
        return payload
    except Exception:
        return {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}


def compute_messaging_metrics(insight: dict, sdk_data: dict | None, actions: list | None, spend) -> dict:
    """
    Unifica KPIs de mensajería con prioridad: SDK > insight > derivado de actions.
    Devuelve SIEMPRE:
      - messaging_conversations_started, messaging_first_reply
      - cost_per_message, cost_per_messaging_first_reply, cost_per_messaging_conversation_started (OFICIAL)
      - mensajes_total, costo_por_mensaje_total, msg_cost_is_calculated
      - messages_source: 'sdk' | 'insight' | 'derived' (según la fuente más fuerte utilizada)
    """
    def _to_int(x):
        try:
            return int(float(x))
        except Exception:
            return 0
    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return None
    out = {
        "messaging_conversations_started": 0,
        "messaging_first_reply": 0,
        "cost_per_message": None,
        "cost_per_messaging_first_reply": None,
        "cost_per_messaging_conversation_started": None,  # ← oficial de insights
        "mensajes_total": 0,
        "costo_por_mensaje_total": None,
        "msg_cost_is_calculated": False,
        "messages_source": "derived",
    }
    # 1) SDK primero
    if sdk_data:
        ms = _to_int(sdk_data.get("messages_started"))
        fr = _to_int(sdk_data.get("first_replies"))
        out["messaging_conversations_started"] = max(out["messaging_conversations_started"], ms)
        out["messaging_first_reply"] = max(out["messaging_first_reply"], fr)
        out["cost_per_message"] = _to_float(sdk_data.get("cost_per_message") or sdk_data.get("cost_per_1_message"))
        # si el SDK trae costo por "first reply" en alguna versión futura:
        cfr = _to_float(sdk_data.get("cost_per_messaging_first_reply"))
        if cfr is not None:
            out["cost_per_messaging_first_reply"] = cfr
        out["messages_source"] = "sdk"
    # 2) Insight directo (oficial)
    if insight:
        mcs = _to_int(insight.get("messaging_conversations_started"))
        if mcs > out["messaging_conversations_started"]:
            out["messaging_conversations_started"] = mcs
            if out["messages_source"] != "sdk":
                out["messages_source"] = "insight"
        cpmcs = _to_float(insight.get("cost_per_messaging_conversation_started"))
        if cpmcs is not None:
            out["cost_per_messaging_conversation_started"] = cpmcs
            if out["messages_source"] != "sdk":
                out["messages_source"] = "insight"
    # 3) Derivado de actions (fallback) - USANDO LA FUNCIÓN CORREGIDA
    if actions:
        # Llamar la función que ya arreglamos para procesar actions correctamente
        derived_messages = _derive_messages_from_actions({"actions": actions})
        if derived_messages > out["messaging_conversations_started"] and out["messages_source"] == "derived":
            out["messaging_conversations_started"] = derived_messages
        
        # Procesar first replies con los mismos tipos que _MSG_TYPES
        first = 0
        FIRST_REPLY_ACTIONS = {
            "messaging_first_reply", "first_reply",
            "onsite_conversion.messaging_first_reply",
            "onsite_conversion.messaging_conversation_replied_7d"
        }
        for a in actions:
            n = (a.get("action_type") or "").lower()
            val = _to_int(a.get("value"))
            if n in FIRST_REPLY_ACTIONS:
                first += val
        if first > out["messaging_first_reply"] and out["messages_source"] == "derived":
            out["messaging_first_reply"] = first
    # 4) Agregada y costo calculado
    out["mensajes_total"] = (out["messaging_conversations_started"] or 0) + (out["messaging_first_reply"] or 0)
    if (out["mensajes_total"] or 0) > 0:
        c = _to_float(spend)
        if c is not None:
            out["costo_por_mensaje_total"] = c / max(out["mensajes_total"], 1)
            out["msg_cost_is_calculated"] = True
    return out


def sync_backfill_messaging(account_id: str, start_date: str, end_date: str, nombre_nora=None):
    """Backfill utility that fetches insights for the given account and upserts only messaging+name columns.

    This is a non-public util intended for targeted backfills.
    """
    # Resolve access token (try resolver via env fallback)
    access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
    if not access_token:
        print("FALTA INSUMO: access_token (META_ACCESS_REDACTED_TOKEN) no disponible")
        return {'ok': False, 'error': 'FALTA INSUMO: access_token'}

    # Build endpoint and params
    base_account_id = _normalizar_account_id(account_id)
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/act_{base_account_id}/insights"
    api_version = os.getenv("META_API_VERSION", "v23.0")
    fields_list = load_fields(level="ad", version=api_version, pub=True, act=True)
    params = {
        'access_token': access_token,
        'level': 'ad',
        'breakdowns': 'publisher_platform',
        'action_breakdowns': 'action_type',
        'time_range': json.dumps({'since': start_date, 'until': end_date}),
        'fields': ','.join(fields_list),
        'limit': 500,
    }

    insights = _paginar_insights(url, params)
    if not insights:
        return {'ok': True, 'processed': 0}

    upserts = 0
    for ins in insights:
        ad_id = ins.get('ad_id')
        if not ad_id:
            continue
        # Validar que ad_id sea string antes de llamar get_names_cached
        if isinstance(ad_id, str) and ad_id.strip() and access_token:
            names = get_names_cached(ad_id.strip(), access_token)
        else:
            names = {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}
        sdk_kpis = None
        # try to get SDK messaging kpis via insights_mensajes if available
        try:
            if callable(init_business):
                try:
                    init_business(access_token=access_token or "")
                except Exception:
                    pass
            if callable(insights_mensajes):
                try:
                    sdk_res = insights_mensajes(
                        scope='ad',
                        ids=[ad_id],
                        since=start_date,
                        until=end_date,
                        time_increment='1',
                        retry=1,
                        nombre_nora=nombre_nora or "",
                        empresa_id="",
                    )
                except Exception:
                    sdk_res = None
                if isinstance(sdk_res, dict):
                    sdk_kpis = sdk_res.get(str(ad_id)) or sdk_res
                else:
                    sdk_kpis = getattr(sdk_res, 'raw', None) or sdk_res
            else:
                sdk_kpis = None
        except Exception:
            sdk_kpis = None
        metrics = compute_messaging_metrics(ins, sdk_kpis, ins.get('actions', []), float(ins.get('spend') or 0))
        partial = {
            'ad_id': str(ad_id),
            'fecha_inicio': ins.get('date_start'),
            'fecha_fin': ins.get('date_stop'),
            'publisher_platform': ins.get('publisher_platform') or 'unknown',
            'importe_gastado': float(ins.get('spend') or 0),
            'nombre_campana': ins.get('campaign_name') or names.get('campaign_name'),
            'nombre_conjunto': ins.get('adset_name') or names.get('adset_name'),
        }
        # Expand partial with extra naming/cost/source fields before filtering
        # Normalizar fechas: preferir las del insight; si faltan, usar los parámetros del backfill
        _fecha_inicio = ins.get("date_start") or start_date
        _fecha_fin = ins.get("date_stop") or end_date
        partial.update({
            "ad_id": ad_id,
            "campana_id": ins.get("campaign_id"),
            "conjunto_id": ins.get("adset_id"),
            "id_cuenta_publicitaria": account_id,
            "publisher_platform": ins.get("publisher_platform") or "facebook",
            "fecha_inicio": _fecha_inicio,
            "fecha_fin": _fecha_fin,
            "importe_gastado": _float_or_none(ins.get("spend")),
            # nombres (anuncio/campaña/conjunto)
            "nombre_anuncio": ins.get("ad_name") or names.get("ad_name") or str(ad_id),
            "nombre_campana": ins.get("campaign_name") or names.get("campaign_name"),
            "nombre_conjunto": ins.get("adset_name") or names.get("adset_name"),
            # status de campaña y conjunto (insight → cache Graph → fallbacks)
            "status_campana": ins.get("campaign_status") or ins.get("campaign_effective_status") or names.get("campaign_status"),
            "status_conjunto": ins.get("adset_status") or ins.get("adset_effective_status") or names.get("adset_status"),
            # costo oficial de insights (si viene)
            "cost_per_messaging_conversation_started": _float_or_none(ins.get("cost_per_messaging_conversation_started")),
            # fuente de mensajes
            "messages_source": metrics.get("messages_source"),
        })

        # Add messaging columns only if allowed
        if HAS_NEW_MSG_COLS:
            def _float_or_none(v):
                try:
                    return float(v) if v is not None else None
                except Exception:
                    return None
            partial.update({
                'messaging_conversations_started': int(metrics.get('messaging_conversations_started') or 0),
                'messaging_first_reply': int(metrics.get('messaging_first_reply') or 0),
                'cost_per_message': _float_or_none(metrics.get('cost_per_message')),
                'mensajes_total': int(metrics.get('mensajes_total') or 0),
                'costo_por_mensaje_total': _float_or_none(metrics.get('costo_por_mensaje_total')),
                'msg_cost_is_calculated': bool(metrics.get('msg_cost_is_calculated') or False),
            })

        # Filter to ALLOWED_COLUMNS to avoid PostgREST errors
        to_upsert = {k: v for k, v in partial.items() if k in ALLOWED_COLUMNS}
        try:
            supabase.table('meta_ads_anuncios_detalle').upsert(to_upsert, on_conflict='ad_id,fecha_inicio,fecha_fin,publisher_platform').execute()
            upserts += 1
        except Exception as e:
            print(f"Error upserting backfill for ad {clean_surrogates(str(ad_id))}: {clean_surrogates(str(e))}")
    return {'ok': True, 'processed': upserts}


def _normalizar_account_id(ad_account_id: str) -> str:
    """
    Normaliza el ID de cuenta publicitaria removiendo el prefijo 'act_' si existe
    para evitar duplicar el prefijo en la URL
    """
    return ad_account_id[4:] if ad_account_id.startswith('act_') else ad_account_id


def _paginar_insights(url: str, params: dict, timeout: int = 30) -> list:
    """
    Pagina a través de todas las páginas de insights de la API de Meta
    """
    all_insights = []
    current_url = url
    current_params = params
    
    while True:
        try:
            print(f"📊 Obteniendo página de insights...")
            response = requests.get(current_url, params=current_params, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            page_insights = data.get('data', [])
            all_insights.extend(page_insights)
            
            print(f"   ✅ Página obtenida: {len(page_insights)} insights")
            
            # Verificar si hay siguiente página
            next_url = (data.get('paging') or {}).get('next')
            if not next_url:
                break
            
            # Para siguientes páginas, usar la URL completa que ya incluye parámetros
            current_url = next_url
            current_params = None  # La URL next ya incluye todos los parámetros
            
            # Backoff simple para evitar rate limit
            time.sleep(0.4)
            
        except Exception as e:
            print(f"❌ Error en paginación de insights: {clean_surrogates(str(e))}")
            break
    
    return all_insights


def sincronizar_cuenta_meta_ads_simple(ad_account_id, access_token, fecha_inicio, fecha_fin, nombre_nora=None):
    print(f"🔄 Sincronizando cuenta: {clean_surrogates(str(ad_account_id))}")
    # --- Debug controls (silenciosos por defecto) ---
    LOG_DEBUG = os.getenv("META_SYNC_DEBUG", "0") == "1"
    LOG_EVERY = int(os.getenv("META_SYNC_LOG_EVERY", "100") or "100")
    def _dbg(msg: str) -> None:
        if LOG_DEBUG:
            try:
                print(msg)
            except Exception:
                pass
    
    # Normalizar ID de cuenta para evitar duplicar 'act_' en la URL
    base_account_id = _normalizar_account_id(ad_account_id)
    
    # Construir URL para insights de anuncios
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/act_{base_account_id}/insights"
    
    api_version = os.getenv("META_API_VERSION", "v23.0")
    fields_list = load_fields(level="ad", version=api_version, pub=True, act=True)
    # Asegurar que pedimos 'objective' en los fields (para guardar objetivo_campana)
    if 'objective' not in fields_list:
        fields_list.append('objective')
    # Fix: Asegurar que pedimos 'ad_id' en los fields (requerido para procesamiento)
    if 'ad_id' not in fields_list:
        fields_list.append('ad_id')
    # Params para HTTP (strings)
    params = {
        'access_token': access_token,
        'level': 'ad',
        'breakdowns': 'publisher_platform',
        'action_breakdowns': 'action_type',
        'action_attribution_windows': ['1d_view', '7d_click'],
        'time_range': json.dumps({'since': fecha_inicio.strftime('%Y-%m-%d'), 'until': fecha_fin.strftime('%Y-%m-%d')}),
        'fields': ','.join(fields_list),
        'limit': 500,
    }

    print(f"📊 Usando fields_count={len(fields_list)} para account {clean_surrogates(str(ad_account_id))}")

    print(f"📊 Obteniendo insights entre {clean_surrogates(fecha_inicio.strftime('%Y-%m-%d'))} y {clean_surrogates(fecha_fin.strftime('%Y-%m-%d'))}")
    try:
        # 1) Intento por SDK (Marketing API) usando el util fb_sdk
        # (SDK)
        all_insights = []
        try:
            init_business(access_token=access_token)
            # ✅ Usa el helper estable del util (maneja retries, params y normaliza salida)
            # CORRECCIÓN: Business SDK requiere breakdowns como LISTAS, no strings
            sdk_res = insights_generic(
                scope="account",
                ids=[f"act_{base_account_id}"],
                fields=fields_list,
                params={
                    "level": "ad",
                    "breakdowns": ["publisher_platform"],  # Lista, no string
                    "action_breakdowns": ["action_type"],  # Lista, no string
                    "action_attribution_windows": ["1d_view", "7d_click"],
                    "limit": 500,
                },
                since=fecha_inicio.strftime("%Y-%m-%d"),
                until=fecha_fin.strftime("%Y-%m-%d"),
                time_increment=None,
                retry=1,
                page_limit=500,
            )
            all_insights = sdk_res.raw or []
            print(f"📊 (SDK) Total de insights obtenidos: {len(all_insights)}")
        except ImportError:
            print("ℹ️ SDK de Marketing no disponible; usando fallback HTTP.")
        except Exception as e:
            print(f"⚠️ Error inicializando SDK: {clean_surrogates(str(e))} — fallback HTTP.")

        # 2) Fallback HTTP si el SDK no devolvió datos
        # (HTTP)
        if not all_insights:
            all_insights = _paginar_insights(url, params)
            print(f"📊 (HTTP) Total de insights obtenidos: {len(all_insights)}")

        if not all_insights:
            print(f"⚠️ No se encontraron insights para la cuenta {clean_surrogates(str(base_account_id))}")
            # Intentar sin breakdown y también paginar
            params_simple = params.copy()
            del params_simple['breakdowns']
            print("🔄 Intentando sin breakdown de plataforma...")

            all_insights = _paginar_insights(url, params_simple)
            print(f"📊 Sin breakdown - Total insights: {len(all_insights)}")

        # Debug adicional: mostrar estructura de un insight (SIN contenido problemático)
        if all_insights and len(all_insights) > 0:
            print(f"🔍 Ejemplo de insight para debug:")
            sample_insight = all_insights[0]
            # Limpiar claves que pueden tener surrogates
            safe_keys = []
            for key in sample_insight.keys():
                if isinstance(key, str):
                    safe_key = key.encode('utf-8', errors='ignore').decode('utf-8')
                    safe_keys.append(safe_key)
                else:
                    safe_keys.append(str(key))
            print(f"   Campos disponibles: {clean_surrogates(str(safe_keys))}")
            if 'actions' in sample_insight:
                # Limpiar tipos de acciones también
                safe_action_types = []
                for action in sample_insight.get('actions', []):
                    action_type = action.get('action_type', '')
                    if isinstance(action_type, str):
                        safe_action_type = action_type.encode('utf-8', errors='ignore').decode('utf-8')
                        safe_action_types.append(safe_action_type)
                    else:
                        safe_action_types.append(str(action_type))
                print(f"   Tipos de acciones: {clean_surrogates(str(safe_action_types))}")

        fecha_sync = datetime.utcnow().isoformat()
        # --- Obtener KPIs de mensajería por lotes usando insights_mensajes (SDK primero) ---
        # Nota: según contrato congelado, no se pasan nombre_nora/empresa_id al helper.
        ad_to_rows = {}
        ad_ids_ordered = []
        for idx, insight in enumerate(all_insights):
            aid = insight.get('ad_id')
            if not aid:
                continue
            if aid not in ad_to_rows:
                ad_to_rows[aid] = []
                ad_ids_ordered.append(aid)
            ad_to_rows[aid].append(idx)
        BATCH_SIZE = 1  # forzamos 1 para asegurar que el util procese por ad_id
        kpis_by_ad = {}
        # Llamada SDK-first a insights_mensajes por lotes. Si falla, seguimos usando el parseo de actions
        if ad_ids_ordered:
            # Intentar obtener empresa_id a partir de meta_ads_cuentas (pero NO abortar si falta)
            empresa_id = None
            try:
                resp = supabase.table('meta_ads_cuentas') \
                    .select('empresa_id') \
                    .eq('id_cuenta_publicitaria', ad_account_id) \
                    .eq('nombre_nora', nombre_nora) \
                    .single() \
                    .execute()
                d = getattr(resp, 'data', None)
                if isinstance(d, dict):
                    empresa_id = d.get('empresa_id')
                elif isinstance(d, list) and len(d) > 0:
                    empresa_id = d[0].get('empresa_id')
            except Exception:
                empresa_id = None

            # Inicializar SDK UNA sola vez para todos los batches de mensajes
            sdk_available = True
            try:
                init_business(access_token=access_token)
            except ImportError:
                sdk_available = False
                print("(HTTP parse mensajes) SDK no disponible; usaré parseo de actions")
            except Exception:
                sdk_available = False
                print("(HTTP parse mensajes) error inicializando SDK de mensajes; usaré parseo de actions")

            if sdk_available:
                _dbg(f"💬 (SDK mensajes) Total ad_ids a procesar: {len(ad_ids_ordered)} • batch_size={BATCH_SIZE}")
                # ad_ids únicos presentes en los insights
                ad_ids = [row.get('ad_id') for row in all_insights if row.get('ad_id')]
                ad_ids = list({aid for aid in ad_ids if aid})
                if ad_ids:
                    total_batches = (len(ad_ids) + BATCH_SIZE - 1) // BATCH_SIZE
                    for i in range(0, len(ad_ids), BATCH_SIZE):
                        batch = ad_ids[i:i+BATCH_SIZE]
                        _dbg(f"💬 (SDK mensajes) Batch {i//BATCH_SIZE + 1}/{total_batches}: {batch[:3]}{' …' if len(batch)>3 else ''}")
                        try:
                            # Llamar insights_mensajes pasando siempre strings (vacío si faltan)
                            try:
                                k_res = insights_mensajes(
                                    scope='ad',
                                    ids=batch,
                                    since=fecha_inicio.strftime('%Y-%m-%d'),
                                    until=fecha_fin.strftime('%Y-%m-%d'),
                                    time_increment='1',
                                    retry=1,
                                    nombre_nora=nombre_nora or "",
                                    empresa_id=str(empresa_id) if empresa_id is not None else "",
                                )
                            except Exception:
                                _dbg("⚠️ (SDK mensajes) excepción en llamada primaria; intento vacío -> {}")
                                k_res = {}

                            # Normalizar resultado a dict[id->kpi]
                            if isinstance(k_res, dict):
                                # Normaliza llaves a str para que coincidan con ad_id (string) de all_insights
                                k_res_norm = {str(k): v for k, v in k_res.items()}
                                _keys = list(k_res_norm.keys())
                                _dbg(f"💬 (SDK mensajes) Respuesta dict con {len(_keys)} ids; ejemplo: {_keys[:5]}")
                                kpis_by_ad.update(k_res_norm)
                            else:
                                raw_attr = getattr(k_res, 'raw', None)
                                try:
                                    items = list(raw_attr) if raw_attr is not None else list(k_res)
                                except Exception:
                                    items = None
                                if items:
                                    _dbg(f"💬 (SDK mensajes) Respuesta list-like con {len(items)} filas")
                                    for item in items:
                                        if isinstance(item, dict):
                                            aid = item.get('ad_id') or item.get('id')
                                            if aid:
                                                kpis_by_ad[aid] = item
                                else:
                                    _dbg(f"(HTTP parse mensajes) formato inesperado de insights_mensajes para batch {i//BATCH_SIZE + 1}")

                        except Exception:
                            # Mantener mensajes mínimos, sin PII
                            _dbg(f"(HTTP parse mensajes) error en batch {i//BATCH_SIZE + 1}")

                    if kpis_by_ad:
                        _dbg(f"💬 (SDK mensajes) KPIs obtenidos para {len(kpis_by_ad)} anuncios (unique)")
                    else:
                        _dbg("⚠️ (SDK mensajes) No se obtuvieron KPIs del util para ningún anuncio")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error obteniendo insights para cuenta {clean_surrogates(str(base_account_id))}: {clean_surrogates(str(error_msg))}")
        
        # Diagnóstico específico del error
        if "Invalid OAuth access token" in error_msg:
            print("🔑 Problema de autenticación - token inválido o expirado")
        elif "Unsupported get request" in error_msg:
            print("🚫 Cuenta publicitaria no existe o sin permisos")
        elif "timeout" in error_msg.lower():
            print("⏱️ Timeout en la consulta - API de Meta sobrecargada")
        elif "rate limit" in error_msg.lower():
            print("🚦 Límite de tasa excedido - demasiadas consultas")
        
        return False

    # Actualizar registros existentes como inactivos
    supabase.table('meta_ads_anuncios_detalle') \
        .update({'activo': False, 'fecha_ultima_actualizacion': fecha_sync}) \
        .eq('id_cuenta_publicitaria', ad_account_id).execute()

    anuncios_procesados = 0
    anuncios_con_mensajes = 0
    _util_hits = 0
    _http_hits = 0
    for insight in all_insights:
        # Fix: En insights de Meta API, el ad_id puede venir como 'id' o 'ad_id'
        ad_id = insight.get('ad_id') or insight.get('id')
        
        # DEBUG temporal: ver qué campos están disponibles si no hay ad_id
        if not ad_id and os.getenv('META_SYNC_DEBUG') == '1':
            print(f"⚠️ Insight sin ad_id. Campos disponibles: {clean_surrogates(str(list(insight.keys())[:15]))}...")
            # Intentar reconstruir desde otros campos disponibles
            campaign_id = insight.get('campaign_id') 
            adset_id = insight.get('adset_id')
            platform = insight.get('publisher_platform', 'unknown')
            spend = insight.get('spend', 0)
            if campaign_id and adset_id:
                # Crear un ID temporal usando hash de los datos únicos
                ad_id = f"synthetic_{campaign_id}_{adset_id}_{platform}_{hash(str(insight.get('actions', [])))}"
                print(f"🔧 Usando ad_id sintético: {clean_surrogates(str(ad_id[:50]))}...")
        
        if not ad_id:
            continue

        ad_info = obtener_info_anuncio(ad_id, access_token)
        platform = insight.get('publisher_platform') or 'unknown'

        # Función helper para manejar campos que pueden ser listas de acciones o números
        def safe_int_or_list(value):
            if isinstance(value, list):
                return sum(int(item.get('value', 0) or 0) for item in value if isinstance(item, dict))
            else:
                return int(value or 0)

        # nombre (fallback estable): ad_name -> ad_info.name -> ad_id
        nombre_anuncio = (
            insight.get('ad_name')
            or (ad_info.get('name') if ad_info else None)
            or str(ad_id)
        )

        # mapear campos estándar ya existentes...
        data: dict = {
            'ad_id': str(insight.get('ad_id') or ad_id or ''),
            'nombre_anuncio': nombre_anuncio,
            'id_cuenta_publicitaria': ad_account_id,
            'campana_id': str(insight.get('campaign_id') or ''),
            'conjunto_id': str(insight.get('adset_id') or ''),
            'objetivo_campana': insight.get('objective') or 'UNKNOWN',  # 🆕 Objetivo de campaña
            'importe_gastado': float(insight.get('spend', 0) or 0.0),
            'alcance': safe_int_or_list(insight.get('reach', 0)),
            'impresiones': safe_int_or_list(insight.get('impressions', 0)),
            'clicks': safe_int_or_list(insight.get('clicks', 0)),
            'link_clicks': safe_int_or_list(insight.get('link_clicks', 0)),
            'inline_link_clicks': safe_int_or_list(insight.get('inline_link_clicks', 0)),
            'frequency': float(insight.get('frequency', 0) or 0.0),
            'ctr': float(insight.get('ctr', 0) or 0.0),
            'cpc': float(insight.get('cpc', 0) or 0.0),
            'cost_per_1k_impressions': float(insight.get('cpm', 0) or 0.0),
            'status': ad_info.get('status'),
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'fecha_sincronizacion': fecha_sync,
            'fecha_ultima_actualizacion': fecha_sync,
            'activo': True,
            'publisher_platform': platform,
            'actions': insight.get('actions') or [],
            # NUEVO: guardamos el objetivo tal como lo entrega Meta (string)
            'objetivo_campana': insight.get('objective') or None,
            # CRÍTICO: Agregar nombre_nora para evitar constraint violation
            'nombre_nora': nombre_nora or '',
        }

        # Extraer acciones
        actions = insight.get('actions', [])
        # Debug: Mostrar todas las acciones disponibles
        if actions:
            print(f"📋 Acciones disponibles para anuncio {clean_surrogates(str(ad_id))}: {clean_surrogates(str([action.get('action_type') for action in actions]))}")

        # Parse actions into dict
        actions_dict = {}
        if isinstance(actions, list):
            for a in actions:
                k = a.get("action_type")
                v = a.get("value")
                if k:
                    try:
                        actions_dict[k] = float(v)
                    except Exception:
                        actions_dict[k] = 0.0

        # Map de acciones → "mensajes iniciados" con prioridad canónica.
        # Considera variantes con/sin prefijo y alternativas legacy.
        messaging_actions = [
            # 1) Preferidas (started)
            "onsite_conversion.messaging_conversation_started",
            "onsite_conversion.messaging_conversation_started_7d",
            # 2) Alternativas sin prefijo
            "messaging_conversation_started",
            "messaging_conversation_started_7d",
            # 3) Conexiones totales (aprox. de "iniciados")
            "onsite_conversion.total_messaging_connection",
            "total_messaging_connection",
            # 4) Último recurso: primera respuesta
            "onsite_conversion.messaging_first_reply",
            "messaging_first_reply",
            # 5) Legacy/ambiguo (último)
            "onsite_conversion.total_messaging",
        ]

        # Initialize vía util (si hay KPIs) o por parseo HTTP como fallback
        data['messaging_conversations_started'] = 0
        data.setdefault('messaging_first_reply', 0)
        data.setdefault('cost_per_message', None)

        # 1) Preferir KPIs del util si existen
        # Id del anuncio como string para logs y merge
        ad_id_str = str(ad_id or data.get('ad_id') or insight.get('ad_id') or insight.get('id') or "unknown")
        util_kpis = kpis_by_ad.get(ad_id_str)
        if util_kpis:
            try:
                ms = int(util_kpis.get('messages_started') or 0)
            except Exception:
                ms = int(util_kpis.get('messaging_conversations_started') or 0) if util_kpis.get('messaging_conversations_started') is not None else 0
            try:
                fr = int(util_kpis.get('first_replies') or 0)
            except Exception:
                fr = int(util_kpis.get('messaging_first_reply') or 0) if util_kpis.get('messaging_first_reply') is not None else 0
            cpm = util_kpis.get('cost_per_message') or util_kpis.get('cost_per_1_message') or None
            # Asignar
            data['messaging_conversations_started'] = ms
            data['messaging_first_reply'] = fr
            try:
                data['cost_per_message'] = float(cpm) if cpm is not None else None
            except Exception:
                data['cost_per_message'] = None
            if ms > 0:
                anuncios_con_mensajes += 1
                _util_hits += 1
            # Log compacto por anuncio cuando venga del util
            if (anuncios_procesados % 50) == 0:
                print(f"💬 (SDK mensajes) ad_id={clean_surrogates(str(ad_id_str))} → ms={data['messaging_conversations_started']}, fr={data['messaging_first_reply']}")
        else:
            # 2) Fallback: preferir campo directo del insight si viene, sino derivar de actions
            mcs_val = insight.get('messaging_conversations_started')
            try:
                mcs_int = int(float(mcs_val)) if mcs_val is not None else None
            except Exception:
                mcs_int = None
            if mcs_int is None or mcs_int == 0:
                # derivar desde actions (started_7d, first_reply, total_messaging_connection)
                mcs_int = _derive_messages_from_actions(insight)
                if mcs_int and mcs_int > 0:
                    anuncios_con_mensajes += 1
                    _http_hits += 1
            else:
                # si viene directamente del insight
                anuncios_con_mensajes += 1
                _http_hits += 1
            data['messaging_conversations_started'] = int(mcs_int or 0)
            # costo por mensaje si disponible
            cpm_msg = insight.get('cost_per_messaging_conversation_started')
            if cpm_msg is not None:
                try:
                    data['cost_per_messaging_conversation_started'] = float(cpm_msg)
                except Exception:
                    pass
            if (anuncios_procesados % 50) == 0:
                print(f"💬 (HTTP parse mensajes) ad_id={clean_surrogates(str(ad_id_str))} → ms={data['messaging_conversations_started']}")

        # === Mapeo estable para el agregador semanal ===
        # Asegura que la fila detalle lleve 'mensajes' (alias estable)
        try:
            data['mensajes'] = int(data.get('messaging_conversations_started') or 0)
        except Exception:
            data['mensajes'] = 0
        # Aggregate video action lists if present
        def sum_actions_field(field):
            if field is None:
                return 0
            if isinstance(field, list):
                s = 0
                for it in field:
                    try:
                        s += int(float(it.get('value', 0)))
                    except Exception:
                        continue
                return s
            try:
                return int(float(field))
            except Exception:
                return 0

        vpa = insight.get('video_play_actions') or []
        vpa_total = sum_actions_field(vpa)
        thruplays = sum_actions_field(insight.get('video_thruplay_watched_actions'))
        video_p25 = sum_actions_field(insight.get('video_p25_watched_actions'))
        video_p50 = sum_actions_field(insight.get('video_p50_watched_actions'))
        video_p75 = sum_actions_field(insight.get('video_p75_watched_actions'))
        video_p100 = sum_actions_field(insight.get('video_p100_watched_actions'))
        video_30s = sum_actions_field(insight.get('video_30_sec_watched_actions'))

        # Legacy mappings (enforce numeric defaults and division-safe operations)
        reach = int(insight.get('reach', 0) or 0)
        clicks = int(insight.get('clicks', 0) or 0)
        
        # Usar la función safe_int_or_list definida arriba
        inline_link_clicks = safe_int_or_list(insight.get('inline_link_clicks', 0))
        outbound_clicks = safe_int_or_list(insight.get('outbound_clicks', 0))
        
        ctr = float(insight.get('ctr', 0) or 0.0)
        cpc = float(insight.get('cpc', 0) or 0.0)

        data['unique_impressions'] = reach
        data['unique_clicks'] = clicks
        data['unique_inline_link_clicks'] = inline_link_clicks
        data['unique_outbound_clicks'] = outbound_clicks
        data['unique_ctr'] = ctr
        data['cost_per_unique_click'] = cpc if cpc is not None else (float(insight.get('spend', 0) or 0.0) / clicks if clicks > 0 else 0.0)

        # cost_per_unique_inline_link_click: prefer API field, otherwise compute, default 0.0
        try:
            if insight.get('cost_per_inline_link_click') is not None:
                data['cost_per_unique_inline_link_click'] = float(insight.get('cost_per_inline_link_click') or 0.0)
            else:
                data['cost_per_unique_inline_link_click'] = (float(insight.get('spend', 0) or 0.0) / inline_link_clicks) if inline_link_clicks > 0 else 0.0
        except Exception:
            data['cost_per_unique_inline_link_click'] = 0.0

        data['thruplays'] = thruplays or 0
        try:
            imps = safe_int_or_list(insight.get('impressions', 0))
            data['thruplay_rate'] = (thruplays / imps) if imps > 0 else 0.0
        except Exception:
            data['thruplay_rate'] = 0.0

        data['video_plays'] = vpa_total or 0
        data['video_plays_15s'] = thruplays or 0
        data['video_plays_at_25'] = video_p25 or 0
        data['video_plays_at_50'] = video_p50 or 0
        data['video_plays_at_75'] = video_p75 or 0
        data['video_plays_at_100'] = video_p100 or 0

        # Keep raw video action lists for audit
        data['video_play_actions'] = vpa

        # Completar nombres faltantes y costo oficial
        # Validar que ad_id sea string antes de llamar get_names_cached
        if isinstance(ad_id, str) and ad_id.strip() and access_token:
            names = get_names_cached(ad_id.strip(), access_token)
        else:
            names = {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}
        data["nombre_anuncio"] = data.get("ad_name") or data.get("nombre_anuncio") or names.get("ad_name") or str(ad_id)
        data["nombre_campana"] = data.get("campaign_name") or data.get("nombre_campana") or names.get("campaign_name")
        data["nombre_conjunto"] = data.get("adset_name") or data.get("nombre_conjunto") or names.get("adset_name")
        # status campaña/conjunto: insight → cache Graph → fallbacks comunes de Meta
        data["status_campana"] = (
            data.get("campaign_status")
            or insight.get("campaign_status")
            or insight.get("campaign_effective_status")
            or names.get("campaign_status")
        )
        data["status_conjunto"] = (
            data.get("adset_status")
            or insight.get("adset_status")
            or insight.get("adset_effective_status")
            or names.get("adset_status")
        )
        if "cost_per_messaging_conversation_started" not in data and "cost_per_messaging_conversation_started" in insight:
            # asegurar persistencia del costo oficial si vino en el insight
            try:
                val = insight.get("cost_per_messaging_conversation_started")
                if val is not None:
                    data["cost_per_messaging_conversation_started"] = float(val)
            except Exception:
                pass
        # Remover alias inexistente
        if "mensajes" in data:
            data.pop("mensajes", None)
        # Filtrar estrictamente a columnas permitidas (DDL + nuevas)
        data = {k: v for k, v in data.items() if k in ALLOWED_COLUMNS}
        # Upsert
        supabase.table('meta_ads_anuncios_detalle').upsert(data, on_conflict='ad_id,fecha_inicio,fecha_fin,publisher_platform').execute()
        
        anuncios_procesados += 1

    print(f"✅ Sincronización COMPLETA: {anuncios_procesados} anuncios procesados")
    if anuncios_con_mensajes > 0:
        print(f"💬 Anuncios con mensajes: {anuncios_con_mensajes}")
    else:
        print("💬 Ningún anuncio generó conversaciones por mensajería en este período")
    print(f"   • Hits por util (SDK mensajes): {_util_hits} | Hits por fallback HTTP: {_http_hits}")
    return True


def obtener_info_anuncio(ad_id, access_token):
    """
    Obtiene información adicional del anuncio usando Graph API
    """
    try:
        # 1) Intento por SDK de Graph (util fb_sdk)
        graph = get_graph(access_token)
        fields = 'name,status,campaign{id,name},adset{id,name}'
        # CORRECCIÓN: Pasar version explícitamente en la llamada al método
        info = graph.get_object(ad_id, fields=fields, version=GRAPH_API_VERSION)
        return {
            'name': info.get('name'),
            'status': info.get('status'),
            'campaign_id': (info.get('campaign') or {}).get('id'),
            'campaign_name': (info.get('campaign') or {}).get('name'),
            'adset_id': (info.get('adset') or {}).get('id'),
            'adset_name': (info.get('adset') or {}).get('name'),
        }
    except ImportError:
        # 2) Fallback HTTP si no está el SDK
        try:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ad_id}"
            params = {
                'access_token': access_token,
                'fields': 'name,status,campaign{id,name},adset{id,name}'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            info = response.json()
            return {
                'name': info.get('name'),
                'status': info.get('status'),
                'campaign_id': (info.get('campaign') or {}).get('id'),
                'campaign_name': (info.get('campaign') or {}).get('name'),
                'adset_id': (info.get('adset') or {}).get('id'),
                'adset_name': (info.get('adset') or {}).get('name'),
            }
        except Exception as e2:
            print(f"⚠️ Error HTTP obteniendo info del anuncio {clean_surrogates(str(ad_id))}: {clean_surrogates(str(e2))}")
            return {}
    except Exception as e:
        # 3) Cualquier otro error → intentar HTTP como último recurso
        print(f"⚠️ Error Graph SDK obteniendo info del anuncio {clean_surrogates(str(ad_id))}: {clean_surrogates(str(e))} — fallback HTTP.")
        try:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ad_id}"
            params = {
                'access_token': access_token,
                'fields': 'name,status,campaign{id,name},adset{id,name}'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            info = response.json()
            return {
                'name': info.get('name'),
                'status': info.get('status'),
                'campaign_id': (info.get('campaign') or {}).get('id'),
                'campaign_name': (info.get('campaign') or {}).get('name'),
                'adset_id': (info.get('adset') or {}).get('id'),
                'adset_name': (info.get('adset') or {}).get('name'),
            }
        except Exception as e3:
            print(f"⚠️ Error final obteniendo info del anuncio {clean_surrogates(str(ad_id))}: {clean_surrogates(str(e3))}")
            return {}
