# clientes/aura/routes/panel_cliente_meta_ads/sincronizador_personalizado.py
"""
📊 SCHEMAS DE BD QUE USA ESTE ARCHIVO:

📋 TABLAS PRINCIPALES:
• meta_ads_cuentas: Cuentas publicitarias conectadas
  └ Campos clave: id_cuenta_publicitaria(text), nombre_cliente(text), conectada(boolean)
  
• configuracion_bot: Config de cada Nora (validación multi-tenant)
  └ Campos: nombre_nora(text), modulos(json)

🔗 RELACIONES:
• configuracion_bot -> meta_ads_cuentas via nombre_nora

💡 VERIFICAR SCHEMAS:
from clientes.aura.utils.quick_schemas import existe, columnas
"""

from flask import Blueprint, render_template, request, jsonify, g, current_app, abort
from clientes.aura.utils.supabase_client import supabase
from clientes.aura.utils.nombre_nora import require_nombre_nora, install_nombre_nora_preprocessor

# Función para limpiar caracteres surrogates
def clean_surrogates(text: str) -> str:
    """Limpia caracteres surrogates de una cadena para evitar errores de encoding UTF-8."""
    if not isinstance(text, str):
        return str(text)
    return text.encode('utf-8', errors='ignore').decode('utf-8')
# --- Integración meta_webhook_store para snapshots ---
from clientes.aura.utils.meta.meta_webhook_store import save_ad_snapshot
# Preferir helper string; mantener legacy como fallback
try:
    from clientes.aura.utils.meta.meta_tokens import get_access_token_str, get_access_token as _get_access_token_legacy
except Exception:
    get_access_token_str = None
    _get_access_token_legacy = None
from datetime import datetime, timezone
import json
import os
import uuid
import logging
import csv
import io
from flask import Response
import os
import requests
import math
import time as pytime
from typing import Any, Dict, List, cast, Optional, Union
# --- Normalizador de token Meta universal ---
TokenAny = Union[str, dict, list, None]

# Debug flag
_DBG_MESSAGING = True

# Helpers for report generation
from clientes.aura.utils.meta_ads_recomendaciones import construir_insights_json
from clientes.aura.utils.meta_insights_fields import load_fields
from clientes.aura.utils.meta_ads_cuentas import listar_cuentas_activas
# FB SDK helpers (optional)
try:
    from clientes.aura.utils.fb_sdk import init_business, insights_mensajes
except Exception:
    init_business = None
    insights_mensajes = None

# Try to reuse helpers from tasks to keep logic consistent. If unavailable, provide safe local fallbacks.
try:
    from clientes.aura.tasks.meta_ads_sync_all import (
        compute_messaging_metrics,
        get_names_cached,
        HAS_NEW_MSG_COLS,
        ALLOWED_COLUMNS,
    )
except Exception:
    # Local ROBUST defaults - mirrors meta_ads_sync_all.py logic
    def compute_messaging_metrics(insight, sdk_data, actions, spend):
        """
        🔧 Fallback robusto cuando meta_ads_sync_all.py no está disponible.
        Implementa lógica similar con prioridad: SDK > insight > derivado de actions.
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
        
        # Initialize output with defaults
        out = {
            "messaging_conversations_started": 0,
            "messaging_first_reply": 0,
            "cost_per_message": None,
            "cost_per_messaging_first_reply": None,
            "mensajes_total": 0,
            "costo_por_mensaje_total": None,
            "msg_cost_is_calculated": False,
            "messages_source": "insight"
        }
        
        # 1) SDK primero (si disponible)
        if sdk_data:
            ms = _to_int(sdk_data.get("messages_started"))
            fr = _to_int(sdk_data.get("first_replies"))
            if ms > 0 or fr > 0:
                out["messaging_conversations_started"] = ms
                out["messaging_first_reply"] = fr
                out["cost_per_message"] = _to_float(sdk_data.get("cost_per_message"))
                out["messages_source"] = "sdk"
        
        # 2) Insight directo (si SDK no tiene datos)
        if out["messaging_conversations_started"] == 0:
            mcs = _to_int(insight.get("messaging_conversations_started"))
            if mcs > 0:
                out["messaging_conversations_started"] = mcs
                out["messages_source"] = "insight"
        
        if out["messaging_first_reply"] == 0:
            mfr = _to_int(insight.get("messaging_first_reply"))
            if mfr > 0:
                out["messaging_first_reply"] = mfr
                if out["messages_source"] != "sdk":
                    out["messages_source"] = "insight"
        
        # 3) Derivar desde actions como último recurso
        if out["messaging_conversations_started"] == 0:
            # actions puede ser dict (procesado) o list (original)
            if isinstance(actions, dict):
                # Si es dict procesado, usar la lógica completa
                messaging_actions = [
                    # 1) Preferidas (started)
                    "onsite_conversion.messaging_conversation_started",
                    "onsite_conversion.messaging_conversation_started_7d",
                    # 2) Alternativas sin prefijo
                    "messaging_conversation_started",
                    "messaging_conversation_started_7d",
                    # 3) Conexiones totales (aprox.)
                    "onsite_conversion.total_messaging_connection",
                    "total_messaging_connection",
                    # 4) Último recurso
                    "onsite_conversion.messaging_first_reply",
                    "messaging_first_reply",
                    # 5) Legacy/ambiguo
                    "onsite_conversion.total_messaging",
                ]
                
                for action_key in messaging_actions:
                    if action_key in actions and actions[action_key] > 0:
                        out["messaging_conversations_started"] = _to_int(actions[action_key])
                        out["messages_source"] = "derived"
                        break
            elif isinstance(actions, list):
                # Si es lista original, usar lógica legacy
                messaging_actions = [
                    "onsite_conversion.messaging_conversation_started",
                    "onsite_conversion.messaging_conversation_started_7d",
                    "messaging_conversation_started",
                    "messaging_conversation_started_7d",
                    "onsite_conversion.total_messaging_connection",
                    "total_messaging_connection"
                ]
                total = 0
                for action in actions:
                    if isinstance(action, dict) and action.get("action_type") in messaging_actions:
                        total += _to_int(action.get("value"))
                
                if total > 0:
                    out["messaging_conversations_started"] = total
                    out["messages_source"] = "derived"
        
        # 4) Calcular costos cuando tenemos datos y spend > 0
        spend_float = _to_float(spend) or 0.0
        ms_final = out["messaging_conversations_started"]
        fr_final = out["messaging_first_reply"] 
        
        if spend_float > 0:
            # Costo por mensaje iniciado
            if ms_final > 0 and out["cost_per_message"] is None:
                out["cost_per_message"] = spend_float / ms_final
                out["msg_cost_is_calculated"] = True
            
            # Costo por first reply
            if fr_final > 0:
                out["cost_per_messaging_first_reply"] = spend_float / fr_final
        
        # 5) Totales
        out["mensajes_total"] = ms_final + fr_final
        
        if out["mensajes_total"] > 0 and spend_float > 0:
            out["costo_por_mensaje_total"] = spend_float / out["mensajes_total"]
        
        return out

    def get_names_cached(ad_id, access_token):
        """
        🔧 Fallback robusto para obtener nombres cuando meta_ads_sync_all.py no está disponible.
        Intenta consulta directa a Meta Graph API con timeout corto y error handling.
        """
        if not access_token or not ad_id:
            return {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}
        
        try:
            import requests
            version = os.getenv("META_API_VERSION", "v23.0")
            url = f"https://graph.facebook.com/{version}/{ad_id}"
            params = {
                "access_token": access_token,
                "fields": "name,status,campaign{name,status},adset{name,status}"
            }
            
            resp = requests.get(url, params=params, timeout=5)  # Timeout corto para no bloquear
            if resp.status_code == 200:
                data = resp.json()
                campaign = data.get("campaign", {})
                adset = data.get("adset", {})
                
                return {
                    "campaign_name": campaign.get("name"),
                    "adset_name": adset.get("name"), 
                    "ad_name": data.get("name"),
                    "status": data.get("status"),
                    "campaign_status": campaign.get("status"),
                    "adset_status": adset.get("status")
                }
            else:
                print(f"⚠️ get_names_cached: Meta API error {resp.status_code} for ad {clean_surrogates(str(ad_id))}")
        except Exception as e:
            print(f"⚠️ get_names_cached: Error fetching names for ad {clean_surrogates(str(ad_id))}: {e}")
        
        # Fallback seguro
        return {
            "campaign_name": f"Campaign_{ad_id[:8]}", 
            "adset_name": f"AdSet_{ad_id[:8]}", 
            "ad_name": f"Ad_{ad_id}", 
            "status": "unknown"
        }

    HAS_NEW_MSG_COLS = os.getenv('HAS_NEW_MSG_COLS', '0') == '1'
    try:
        from clientes.aura.utils.supabase_schemas import SUPABASE_SCHEMAS
        ALLOWED_COLUMNS = set(SUPABASE_SCHEMAS.get('meta_ads_anuncios_detalle', {}).keys())
    except Exception:
        ALLOWED_COLUMNS = set()
    # Si queremos escribir columnas nuevas y el schema está desactualizado en memoria,
    # amplia ALLOWED_COLUMNS localmente para no perderlas en el filtrado.
    if HAS_NEW_MSG_COLS:
        ALLOWED_COLUMNS = ALLOWED_COLUMNS.union({
            'messaging_first_reply',
            'mensajes_total',
            'cost_per_message',
            'cost_per_messaging_first_reply',
            'costo_por_mensaje_total',
            'msg_cost_is_calculated',
            'messages_source',
        })

def _normalize_meta_token(value: TokenAny) -> Optional[str]:
    """
    Acepta lo que sea que devuelva get_access_token (str | dict | list | None)
    y devuelve solo el token como str o None.
    - Soporta dict con 'access_token' o 'token'.
    - Soporta lista de dicts/strings (toma el primer válido).
    - Limpia prefijo 'Bearer ' si aparece.
    """
    def _from_dict(d: dict) -> Optional[str]:
        tok = d.get("access_token") or d.get("token")
        if isinstance(tok, str):
            tok = tok.strip()
            if tok.lower().startswith("bearer "):
                tok = tok[7:].strip()
            return tok or None
        return None

    if value is None:
        return None

    if isinstance(value, str):
        v = value.strip()
        if v.lower().startswith("bearer "):
            v = v[7:].strip()
        return v or None

    if isinstance(value, dict):
        return _from_dict(value)

    if isinstance(value, list):
        for item in value:
            # item puede ser str o dict
            if isinstance(item, str):
                t = _normalize_meta_token(item)
                if t:
                    return t
            elif isinstance(item, dict):
                t = _from_dict(item)
                if t:
                    return t
        return None

    # Cualquier otro tipo no soportado
    return None

# Import tolerante para process_queue
try:
    from clientes.aura.utils.meta.meta_webhook_master import process_queue as _process_queue
except Exception:
    _process_queue = None


def _resolver_token_meta(nombre_nora: str) -> Optional[str]:
    """
    Intenta obtener un token de Meta para la nora dada (string).
    Usa helper string; si no está disponible, cae a legacy + normalizador.
    """
    # 1) Helper string (preferido)
    if get_access_token_str:
        try:
            return get_access_token_str(nombre_nora)
        except Exception as e:
            logging.warning(f"_resolver_token_meta: fallo get_access_token_str: {e}")
    # 2) Legacy (puede devolver dict/str), normalizar
    if _get_access_token_legacy:
        try:
            raw = _get_access_token_legacy(nombre_nora)
            return _normalize_meta_token(raw)
        except Exception as e:
            logging.warning(f"_resolver_token_meta: fallo legacy get_access_token: {e}")
    return None

# Helper local para enriquecer pendientes
def enriquecer_pendientes(batch: int = 100) -> dict:
    """
    Wrapper local que usa el util 'process_queue' para procesar eventos pendientes.
    Retorna un dict con resumen para la respuesta del endpoint.
    """
    if _process_queue is None:
        return {"ok": False, "error": "process_queue no disponible (meta_webhook_master no importable)"}
    try:
        procesados = _process_queue(batch=batch)
        if isinstance(procesados, int):
            return {"ok": True, "procesados": procesados}
        elif isinstance(procesados, dict) and "procesados" in procesados:
            return {"ok": True, "procesados": int(procesados.get("procesados", 0)), **procesados}
        else:
            return {"ok": True, "procesados": 0, "detalle": procesados}
    except Exception as e:
        return {"ok": False, "error": f"Error al procesar cola: {e}"}
def _devtools_enabled() -> bool:
    # Habilita endpoints dev si FLASK_ENV=development, DEBUG True o ALLOW_DEVTOOLS=1
    try:
        return bool(current_app.debug) or os.getenv("FLASK_ENV") == "development" or os.getenv("ALLOW_DEVTOOLS") == "1"
    except Exception:
        return os.getenv("ALLOW_DEVTOOLS") == "1"


# --- ENDPOINTS SOLO DEV ---

# Mover los endpoints después de la definición del blueprint

# ...existing code...

# ENDPOINTS DEV Y HEALTH

MAX_DAYS = 90
TERMINAL_STATES = {"success", "error", "canceled"}

# Blueprint para sincronización personalizada (SUB-BLUEPRINT)
sincronizador_personalizado_bp = Blueprint(
    "sincronizador_personalizado_bp", 
    __name__,
    url_prefix="/sincronizador-personalizado"  # ✅ Solo la parte específica del sub-módulo
)

# ✅ SOLUCIÓN: Instalar preprocessor para heredar nombre_nora del blueprint padre
install_nombre_nora_preprocessor(sincronizador_personalizado_bp)

# Almacenamiento temporal en memoria para jobs (hasta implementar persistencia)
sync_jobs = {}

def validar_modulo_meta_ads(nombre_nora):
    """Validación específica del módulo Meta Ads"""
    try:
        result = supabase.table('configuracion_bot') \
            .select('modulos') \
            .eq('nombre_nora', nombre_nora) \
            .single() \
            .execute()
        
        if not result.data:
            return False, "Nora no encontrada"
        
        modulos = result.data.get('modulos', {})
        if not modulos.get('meta_ads'):
            return False, "Módulo Meta Ads no activo"
        
        return True, None
        
    except Exception as e:
        logging.error(f"Error validando módulo Meta Ads para {clean_surrogates(nombre_nora)}: {e}")
        return False, "Error de validación"

# ENDPOINTS DEV Y HEALTH (después de la definición del blueprint)
@sincronizador_personalizado_bp.route("/dev/seed", methods=["POST"])
def dev_seed_pendiente(nombre_nora: str):
    if not _devtools_enabled():
        return jsonify({"ok": False, "error": "Devtools deshabilitado"}), 403

    payload = request.get_json(silent=True) or {}
    tipo_objeto = (payload.get("tipo_objeto") or "").strip()
    objeto_id = (payload.get("objeto_id") or "").strip()
    id_cuenta_publicitaria = (payload.get("id_cuenta_publicitaria") or "").strip()
    campo = (payload.get("campo") or "").strip() or None
    valor = payload.get("valor")

    if not (tipo_objeto and objeto_id and id_cuenta_publicitaria):
        return jsonify({"ok": False, "error": "Faltan campos requeridos: tipo_objeto, objeto_id, id_cuenta_publicitaria"}), 400

    try:
        row = {
            "nombre_nora": nombre_nora,
            "tipo_objeto": tipo_objeto,
            "objeto_id": objeto_id,
            "id_cuenta_publicitaria": id_cuenta_publicitaria,
            "campo": campo,
            "valor": valor,
            "procesado": False,
            "timestamp": "now()"
        }
        _tbl = cast(Any, supabase.table("logs_webhooks_meta"))
        _tbl.insert(row, returning="minimal").execute()
        return jsonify({"ok": True, "inserted": True, "row": {k: v for k, v in row.items() if k != "valor"}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@sincronizador_personalizado_bp.route("/dev/run_once", methods=["POST"])
def dev_run_once(nombre_nora: str):
    if not _devtools_enabled():
        return jsonify({"ok": False, "error": "Devtools deshabilitado"}), 403

    payload = request.get_json(silent=True) or {}
    try:
        batch = int(payload.get("batch", 100))
    except Exception:
        batch = 100
    res = enriquecer_pendientes(batch=batch)
    status = 200 if res.get("ok") else 500
    return jsonify(res), status

@sincronizador_personalizado_bp.route("/health", methods=["GET"])
def health(nombre_nora: str):
    checks = {"db_ok": False, "token_ok": False, "has_pending": False}
    errors: Dict[str, str] = {}
    account_id = request.args.get("account_id")

    # DB check
    try:
        data = supabase.table("meta_ads_cuentas").select("id_cuenta_publicitaria").eq("nombre_nora", nombre_nora).limit(1).execute()
        _ = (data.data or [])
        checks["db_ok"] = True
    except Exception as e:
        errors["db_error"] = str(e)

    # Token check (string preferido; fallback legacy)
    try:
        tok_ok = False
        if get_access_token_str:
            t = get_access_token_str(nombre_nora)
            tok_ok = bool(t)
        elif _get_access_token_legacy:
            raw = _get_access_token_legacy(nombre_nora)
            tok_ok = bool(_normalize_meta_token(raw))
        checks["token_ok"] = tok_ok
    except Exception as e:
        errors["token_error"] = str(e)

    # Cola/pending check
    try:
        q = supabase.table("logs_webhooks_meta").select("id").eq("nombre_nora", nombre_nora).eq("procesado", False).limit(1).execute()
        checks["has_pending"] = bool(q.data)
    except Exception as e:
        errors["queue_error"] = str(e)

    ok = checks["db_ok"] or checks["token_ok"]

    last_job = None
    try:
        last_job = globals().get("sync_jobs", {}).get("last")
    except Exception:
        last_job = None

    payload = {
        "ok": ok,
        "component": "sincronizador_personalizado",
        "nombre_nora": nombre_nora,
        "checks": checks,
        "last_job": last_job
    }
    if errors:
        payload["errors"] = errors
    return jsonify(payload), 200 if ok else 503

@sincronizador_personalizado_bp.route("/")
def vista_sincronizador_personalizado(nombre_nora=None, **view_args):
    # 🔍 DEBUG para ver qué está llegando
    logging.debug(f"view_args: {view_args}")
    logging.debug(f"param nombre_nora directo: {clean_surrogates(str(nombre_nora))}")
    logging.debug(f"g.nombre_nora: {clean_surrogates(str(getattr(g, 'nombre_nora', None)))}")

    try:
        nombre_nora = nombre_nora or require_nombre_nora(allow_path_fallback=True)
        logging.debug(f"require_nombre_nora -> {clean_surrogates(nombre_nora)}")

        valido, error = validar_modulo_meta_ads(nombre_nora)
        if not valido:
            return f"Error: {error}", 403

        return render_template(
            "panel_cliente_meta_ads/sincronizador_personalizado.html",
            nombre_nora=nombre_nora
        )
    except Exception as e:
        logging.error(f"Error en vista sincronizador personalizado: {e}")
        return "Error interno", 500

def _parse_date_yyyy_mm_dd(s: str):
    # Acepta 'YYYY-MM-DD' y retorna datetime.date, lanza ValueError si no
    return datetime.strptime(s, "%Y-%m-%d").date()

def _validate_iniciar_payload(payload):
    # Esperado: {account_id, date_from (YYYY-MM-DD), date_to (YYYY-MM-DD), modo ('completo'|'incremental')}
    required = ("account_id", "date_from", "date_to", "modo")
    for k in required:
        if not payload.get(k):
            return {"ok": False, "error": {"code": "ACCOUNT_REQUIRED" if k=="account_id" else "BAD_RANGE", "message": f"Falta {k}"}}
    try:
        dfrom = _parse_date_yyyy_mm_dd(payload["date_from"])
        dto   = _parse_date_yyyy_mm_dd(payload["date_to"])
    except Exception:
        return {"ok": False, "error": {"code": "BAD_RANGE", "message": "Formato de fechas inválido (YYYY-MM-DD)"}}
    if dfrom > dto:
        return {"ok": False, "error": {"code": "BAD_RANGE", "message": "La fecha 'Desde' no puede ser mayor que 'Hasta'"}}
    span = (dto - dfrom).days + 1
    if span > MAX_DAYS:
        return {"ok": False, "error": {"code": "BAD_RANGE", "message": f"El rango excede el máximo ({MAX_DAYS} días)"}}
    if payload["modo"] not in ("completo", "incremental"):
        return {"ok": False, "error": {"code": "BAD_RANGE", "message": "Modo inválido (use 'completo' o 'incremental')"}}
    return {"ok": True, "date_from": dfrom, "date_to": dto}

def _job_matches_tenant_account(job, nombre_nora, account_id):
    return (job.get("nombre_nora") == nombre_nora) and (job.get("account_id") == account_id) and (job.get("status") in ("queued","running"))

def _normalize_errors(err):
    # Devuelve lista
    if err is None:
        return []
    if isinstance(err, list):
        return err
    return [str(err)]

def _add_job_log(job_id, level, message):
    """Agregar un log al job con timestamp"""
    job = sync_jobs.get(job_id)
    if not job:
        return

    if 'logs' not in job:
        job['logs'] = []

    # Limpiar surrogates del mensaje
    clean_message = clean_surrogates(str(message)) if message else ''

    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': level,  # info, warning, error, success
        'message': clean_message
    }

    job['logs'].append(log_entry)

    # Mantener solo los últimos 100 logs para evitar memory leaks
    if len(job['logs']) > 100:
        job['logs'] = job['logs'][-100:]

@sincronizador_personalizado_bp.route("/iniciar", methods=['POST'])
def iniciar_sincronizacion(nombre_nora=None):
    """Inicia sincronización completa o incremental"""
    try:
        nombre_nora = require_nombre_nora(allow_path_fallback=True)
        # Validar módulo
        valido, error = validar_modulo_meta_ads(nombre_nora)
        if not valido:
            return jsonify({
                "error": {
                    "code": "MODULE_NOT_ACTIVE",
                    "message": error
                }
            }), 403

        # Leer y validar body
        payload = request.get_json(silent=True) or {}
        val = _validate_iniciar_payload(payload)
        if not val["ok"]:
            return jsonify({"error": val["error"]}), 400

        account_id = payload["account_id"]
        # Concurrencia por (tenant, account)
        for jid, job in list(sync_jobs.items()):
            if _job_matches_tenant_account(job, nombre_nora, account_id):
                return jsonify({"error": {"code": "ALREADY_RUNNING", "message": "Ya hay una sincronización en curso para esa cuenta"}}), 409

        # Crear nuevo job
        job_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        sync_jobs[job_id] = {
            "job_id": job_id,
            "nombre_nora": nombre_nora,
            "account_id": payload["account_id"],
            "date_from": payload["date_from"],
            "date_to": payload["date_to"],
            "modo": payload["modo"],
            "status": "queued",
            "progress": 0,
            "processed": 0,
            "total": 1,  # Se ajusta luego
            "message": "Sincronización en cola...",
            "started_at": started_at.isoformat(),
            "finished_at": None,
            "errors": [],
            "error_summary": "",
            "logs": [],
            "current_step": "Sincronización en cola..."
        }
        logging.info(f"Sincronización iniciada para {clean_surrogates(nombre_nora)} - Job ID: {job_id} - Account: {account_id}")
        import threading
        thread = threading.Thread(target=_run_insights_sync, args=(job_id,))
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "queued",
            "job_id": job_id,
            "started_at": started_at.isoformat()
        })
    except Exception as e:
        logging.error(f"Error iniciando sincronización: {e}")
        return jsonify({
            "error": {
                "code": "SYNC_START_ERROR",
                "message": f"Error iniciando sincronización: {str(e)}"
            }
        }), 500

@sincronizador_personalizado_bp.route("/estado")
def obtener_estado_sincronizacion(nombre_nora=None):
    """Obtiene el estado de sincronización actual"""
    try:
        nombre_nora = require_nombre_nora(allow_path_fallback=True)
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({
                "error": {"code": "MISSING_JOB_ID", "message": "job_id requerido"}
            }), 400
        # Buscar job
        job = sync_jobs.get(job_id)
        if not job:
            return jsonify({
                "error": {"code": "JOB_NOT_FOUND", "message": "Job no encontrado"}
            }), 404
        # Verificar que el job pertenece al tenant
        if job.get('nombre_nora') != nombre_nora:
            return jsonify({
                "error": {"code": "JOB_ACCESS_DENIED", "message": "Acceso denegado"}
            }), 403
        # Contrato JSON estándar para /estado
        return jsonify({
            "status": job.get("status", "idle"),
            "progress": job.get("progress", 0),
            "processed": job.get("processed", 0),
            "total": job.get("total", 0),
            "message": job.get("message", ""),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
            "job_id": job_id,
            "account_id": job.get("account_id"),
            "date_from": job.get("date_from"),
            "date_to": job.get("date_to"),
            "modo": job.get("modo"),
            "current_step": job.get("current_step", ""),
            "logs": job.get("logs", [])
        })
    except Exception as e:
        logging.error(f"Error obteniendo estado: {e}")
        return jsonify({
            "error": {
                "code": "STATE_ERROR",
                "message": f"Error obteniendo estado: {str(e)}"
            }
        }), 500

@sincronizador_personalizado_bp.route("/cancelar", methods=['POST'])
def cancelar_sincronizacion(nombre_nora=None):
    """Cancela la sincronización en curso"""
    try:
        nombre_nora = require_nombre_nora(allow_path_fallback=True)
        payload = request.get_json(silent=True) or {}
        req_job_id = payload.get("job_id")
        if req_job_id:
            job = sync_jobs.get(req_job_id)
            if not job or job.get("nombre_nora") != nombre_nora:
                return jsonify({"error": {"code": "JOB_NOT_FOUND", "message": "job_id no encontrado para este tenant"}}), 404
            job["status"] = "canceled"
            job.setdefault("errors", [])
            job["finished_at"] = datetime.utcnow().isoformat()
            return jsonify({"status": "canceled", "job_id": req_job_id}), 200
        # Fallback: cancelar el más reciente activo del tenant
        tenant_jobs = [j for j in sync_jobs.values()
                       if j.get('nombre_nora') == nombre_nora and j.get('status') in ['queued','running']]
        tenant_jobs.sort(key=lambda x: x.get('started_at',''), reverse=True)
        if not tenant_jobs:
            return jsonify({"status": "not_running"})
        job = tenant_jobs[0]
        job_id = job['job_id']
        sync_jobs[job_id].update({
            "status": "canceled",
            "finished_at": datetime.utcnow().isoformat(),
            "message": "Sincronización cancelada por el usuario"
        })
        logging.info(f"Sincronización cancelada para {clean_surrogates(nombre_nora)} - Job ID: {job_id}")
        return jsonify({
            "status": "canceled",
            "job_id": job_id
        })
    except Exception as e:
        logging.error(f"Error cancelando sincronización: {e}")
        return jsonify({
            "error": {
                "code": "CANCEL_ERROR",
                "message": f"Error cancelando sincronización: {str(e)}"
            }
        }), 500

@sincronizador_personalizado_bp.route("/limpiar-jobs", methods=['POST'])
def limpiar_jobs_colgados(nombre_nora=None):
    """Limpia todos los jobs colgados en estado running/queued para el tenant"""
    try:
        nombre_nora = require_nombre_nora(allow_path_fallback=True)
        
        # Buscar jobs colgados del tenant
        jobs_colgados = []
        for job_id, job in list(sync_jobs.items()):
            if (job.get('nombre_nora') == nombre_nora and 
                job.get('status') in ['queued', 'running']):
                jobs_colgados.append(job_id)
                # Marcar como error/cancelado
                sync_jobs[job_id].update({
                    "status": "canceled",
                    "finished_at": datetime.utcnow().isoformat(),
                    "message": "Job limpiado por timeout/error"
                })
        
        return jsonify({
            "ok": True,
            "jobs_limpiados": len(jobs_colgados),
            "job_ids": jobs_colgados
        })
        
    except Exception as e:
        logging.error(f"Error limpiando jobs: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@sincronizador_personalizado_bp.route("/cuentas", methods=["GET"])
def listar_cuentas(nombre_nora=None):
    """
    Devuelve las cuentas publicitarias activas del tenant para poblar el selector.
    Respuesta:
      { "cuentas": [ { "id", "name", "currency", "timezone_name", "has_ads", "message" } ] }
    """
    # 1) Resolver tenant y validar módulo
    try:
        nombre_nora = nombre_nora or require_nombre_nora(allow_path_fallback=True)
        valido, error = validar_modulo_meta_ads(nombre_nora)
        if not valido:
            raise Exception(error or "Tenant inválido")
    except Exception as e:
        print(f"[listar_cuentas] Error de validación: {clean_surrogates(str(e))}")
        return jsonify({"error": {"code": "TENANT_INVALID", "message": str(e)}}), 400

    # 2) Parsear query params opcionales
    def _arg_bool(val: str | None) -> bool:
        return val is not None and val.lower() in ("1","true","t","sí","si","yes","y")
    
    try:
        require_activo = _arg_bool(request.args.get("activo"))
        require_conectada = _arg_bool(request.args.get("conectada"))
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)
    except ValueError:
        return jsonify({"error": {"code": "BAD_REQUEST", "message": "Parámetros limit/offset inválidos"}}), 400

    # 3) Usar util para obtener cuentas
    try:
        cuentas = listar_cuentas_activas(
            nombre_nora=nombre_nora,
            require_activo=require_activo,
            require_conectada=require_conectada,
            limit=limit,
            offset=offset
        )
        return jsonify({"cuentas": cuentas}), 200
    except Exception as e:
        print(f"[listar_cuentas] Error obteniendo cuentas: {clean_surrogates(str(e))}")
        return jsonify({"error": {"code": "SERVER_ERROR", "message": str(e)}}), 500

def _run_insights_sync(job_id):
    try:
        job = sync_jobs.get(job_id)
        if not job:
            return
        
        # Inicializar logs y estado
        sync_jobs[job_id].update({
            "status": "running",
            "message": "Preparando sincronización de Meta Ads Insights...",
            "progress": 0,
            "processed": 0,
            "total": 1,
            "current_step": "Iniciando sincronización..."
        })
        
        _add_job_log(job_id, 'info', 'Iniciando sincronización de insights')
        nombre_nora = job["nombre_nora"]
        account_id = job["account_id"]
        date_from = job["date_from"]
        date_to = job["date_to"]
        modo = job.get("modo", "completo")
        
        # Obtener nombre de la cuenta publicitaria
        cuenta_nombre = "Desconocida"
        try:
            cuenta_data = supabase.table("meta_ads_cuentas").select("nombre_cliente").eq("nombre_nora", nombre_nora).eq("id_cuenta_publicitaria", account_id).single().execute()
            if cuenta_data.data:
                cuenta_nombre = clean_surrogates(cuenta_data.data.get("nombre_cliente", "Desconocida"))
        except Exception:
            pass
        
        _add_job_log(job_id, 'info', f'📊 Cuenta: {clean_surrogates(cuenta_nombre)} ({account_id})')
        _add_job_log(job_id, 'info', f'📅 Rango: {date_from} → {date_to}')
        _add_job_log(job_id, 'info', f'⚙️ Modo: {modo}')

        # 1. Token
        access_token = _resolver_token_meta(nombre_nora)
        if not access_token:
            sync_jobs[job_id].update({
                "status": "error",
                "finished_at": datetime.utcnow().isoformat(),
                "message": "Falta access_token para Meta Ads",
                "error_summary": "MISSING_REDACTED_TOKEN"
            })
            return

        _add_job_log(job_id, 'info', '🔄 Usando sincronizador probado de meta_ads_sync_all...')
        
        # Importar y usar la función probada
        from clientes.aura.tasks.meta_ads_sync_all import sincronizar_cuenta_meta_ads_simple
        
        # Activar debug temporal para ver progreso
        original_debug = os.getenv("META_SYNC_DEBUG")
        os.environ["META_SYNC_DEBUG"] = "1"
        
        try:
            # 🚀 Usar la función probada en lugar de reimplementar todo
            _add_job_log(job_id, 'info', f'🔧 Iniciando sincronización con meta_ads_sync_all para cuenta {account_id}')
            
            # INTERCEPTAR y limpiar datos antes de enviar a la función
            def clean_surrogate_strings(text):
                """Limpia caracteres surrogate que causan problemas de encoding"""
                if not isinstance(text, str):
                    return text
                try:
                    # Remover surrogates y caracteres problemáticos
                    return text.encode('utf-8', errors='ignore').decode('utf-8')
                except:
                    return str(text).encode('ascii', errors='ignore').decode('ascii')
            
            # Pre-limpiar solo parámetros de texto
            safe_account_id = clean_surrogate_strings(str(account_id))
            safe_access_token = clean_surrogate_strings(str(access_token))
            safe_nombre_nora = clean_surrogate_strings(str(nombre_nora))
            
            # Convertir fechas string a objetos date para la función
            from datetime import datetime as dt
            safe_fecha_inicio = dt.strptime(date_from, "%Y-%m-%d").date()
            safe_fecha_fin = dt.strptime(date_to, "%Y-%m-%d").date()
            
            _add_job_log(job_id, 'info', f'🧹 Parámetros limpiados de surrogates y fechas convertidas')
            
            # CRÍTICO: Wrap la llamada con manejo detallado de errores UTF-8
            try:
                result = sincronizar_cuenta_meta_ads_simple(
                    ad_account_id=safe_account_id,
                    access_token=safe_access_token,
                    fecha_inicio=safe_fecha_inicio,
                    fecha_fin=safe_fecha_fin,
                    nombre_nora=safe_nombre_nora
                )
            except (UnicodeEncodeError, UnicodeDecodeError) as encoding_err:
                import traceback
                tb_lines = traceback.format_exception(type(encoding_err), encoding_err, encoding_err.__traceback__)
                tb_str = ''.join(tb_lines)
                _add_job_log(job_id, 'error', f'❌ Error UTF-8 en meta_ads_sync_all: {str(encoding_err)}')
                _add_job_log(job_id, 'error', f'🔍 Traceback UTF-8: {clean_surrogates(tb_str)}')
                print(f"🔍 ERROR UTF-8 EN meta_ads_sync_all: {clean_surrogates(tb_str)}")
                raise encoding_err
            
            # La función retorna info del procesamiento (puede ser bool o dict)
            if result:
                # Manejar tanto bool como dict
                if isinstance(result, dict):
                    processed_count = result.get("count", 0)
                else:
                    processed_count = 1  # Si es True, asumimos al menos 1 registro procesado
                
                _add_job_log(job_id, 'success', f'✅ Sincronización completada: {processed_count} registros procesados')
                
                sync_jobs[job_id].update({
                    "status": "success",
                    "progress": 100,
                    "processed": processed_count,
                    "total": processed_count,
                    "finished_at": datetime.utcnow().isoformat(),
                    "message": f"✅ Sincronización completada ({processed_count} registros)",
                    "error_summary": ""
                })
            else:
                _add_job_log(job_id, 'warning', '⚠️ Sincronización completada sin datos')
                sync_jobs[job_id].update({
                    "status": "success",
                    "progress": 100,
                    "processed": 0,
                    "total": 0,
                    "finished_at": datetime.utcnow().isoformat(),
                    "message": "✅ Sincronización completada (sin datos nuevos)",
                    "current_step": "✅ Completado"
                })
        
        finally:
            # Restaurar configuración original de debug
            if original_debug:
                os.environ["META_SYNC_DEBUG"] = original_debug
            else:
                os.environ.pop("META_SYNC_DEBUG", None)
        
        # Generate account-level weekly-style report after successful sync
        try:
            crear_reporte = job.get("crear_reporte", True)
            if crear_reporte:
                _add_job_log(job_id, 'info', '📋 Generando reporte semanal...')
                _add_job_log(job_id, 'info', '🔧 Ejecutando generar_reporte_para_cuenta...')
                reporte_result = generar_reporte_para_cuenta(nombre_nora, account_id, str(date_from), str(date_to))
                _add_job_log(job_id, 'info', f'📄 Resultado generación: {reporte_result}')
                
                # Verificar si se generó correctamente
                if reporte_result.get("ok"):
                    reporte_token = reporte_result.get("reporte", {}).get("public_token")
                    _add_job_log(job_id, 'success', f'✅ Reporte generado con token: {reporte_token}')
                else:
                    _add_job_log(job_id, 'warning', f'⚠️ Problema generando reporte: {reporte_result.get("msg", "Error desconocido")}')
        except (ValueError, KeyError, AttributeError) as reporte_err:
            _add_job_log(job_id, 'error', f'❌ Error específico generando reporte: {reporte_err}')
            
    except Exception as e:
        # CRÍTICO: Capturar TODOS los errores para evitar jobs colgados
        import traceback
        tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
        tb_str = ''.join(tb_lines)
        _add_job_log(job_id, 'error', f'❌ Error en sincronización: {str(e)}')
        _add_job_log(job_id, 'error', f'🔍 Traceback completo: {clean_surrogates(tb_str)}')
        print(f"🔍 ERROR TRACEBACK: {clean_surrogates(tb_str)}")
        
        # SIEMPRE marcar job como error para que no se quede colgado
        if job_id in sync_jobs:
            sync_jobs[job_id].update({
                "status": "error",
                "finished_at": datetime.utcnow().isoformat(),
                "message": f"Error en sincronización: {str(e)}",
                "error_summary": f"Error en sincronización: {str(e)}"
            })
    
    # CRÍTICO: Return aquí para evitar ejecutar código obsoleto
    return

# ===== FUNCIÓN REFACTORIZADA HASTA AQUÍ =====
# CÓDIGO OBSOLETO ELIMINADO

# --- helpers ---
def _fetch_insights_all_pages(endpoint, params, job_id):
    all_data = []
    url = endpoint
    tries = 0
    max_retries = 5
    backoff = [0.5, 1, 2, 4, 8]
    page = 0
    while url:
        page += 1
        _add_job_log(job_id, 'info', f'Descargando página {page}...')
        
        for attempt in range(max_retries):
            try:
                # Cast url to str for static type checkers (url is guarded by while url: but linters may not infer)
                resp = requests.get(cast(str, url), params=params if page == 1 else None, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    rows = data.get("data", [])
                    all_data.extend(rows)
                    
                    # Progreso tentativo con logs
                    sync_jobs[job_id].update({
                        "message": f"Descargada página {page} ({len(rows)} filas, total {len(all_data)})",
                        "processed": len(all_data),
                        "current_step": f"Descargando página {page}... ({len(all_data)} registros)"
                    })
                    _add_job_log(job_id, 'success', f'Página {page}: {len(rows)} registros obtenidos')
                    
                    # Verificar si hay más páginas
                    if 'paging' in data and 'next' in data['paging']:
                        url = data['paging']['next']
                        _add_job_log(job_id, 'info', 'Hay más páginas disponibles')
                    else:
                        url = None
                        _add_job_log(job_id, 'info', f'Descarga completada: {len(all_data)} registros totales')
                    break
                elif resp.status_code == 429:
                    _add_job_log(job_id, 'warning', f'Rate limit alcanzado en página {page}, esperando...')
                    if attempt < max_retries - 1:
                        pytime.sleep(backoff[attempt])
                        continue
                    else:
                        raise Exception(f"Meta API rate limit tras {max_retries} intentos")
                elif resp.status_code in (500, 502, 503, 504):
                    _add_job_log(job_id, 'warning', f'Error servidor ({resp.status_code}) en página {page}, reintentando...')
                    if attempt < max_retries - 1:
                        pytime.sleep(backoff[attempt])
                        continue
                    else:
                        raise Exception(f"Meta API server error tras {max_retries} intentos: {resp.text}")
                else:
                    raise Exception(f"Meta API error {resp.status_code}: {resp.text}")
            except Exception as e:
                if attempt < max_retries - 1:
                    _add_job_log(job_id, 'warning', f'Error en página {page}, intento {attempt + 1}/{max_retries}')
                    pytime.sleep(backoff[attempt])
                    continue
                else:
                    _add_job_log(job_id, 'error', f'Error final en página {page}: {str(e)}')
                    raise
        params = None  # Solo en la primera página
    return all_data

def _map_insight_to_row(ins, job, now_iso):
    """
    Mapea un insight (nivel ad) a una fila lista para upsert.
    Debe ser defensivo: siempre asignar ad_id y publisher_platform.
    """
    # Validación básica sin debug verboso
    if not isinstance(ins, dict):
        return None
    if not isinstance(job, dict):
        return None
        
    row = {}
    # Asegurar compatibilidad con el nombre "now" usado históricamente dentro de la función
    now = now_iso

    # 1) ad_id SIEMPRE definido antes de usarlo
    ad_id = str(
        (ins.get('ad_id')
         or ins.get('id')
         or (ins.get('ad') or {}).get('id')
         or (ins.get('adset') or {}).get('ad_id')
         or '')
    ).strip()
    
    # 🔧 NUEVO: Manejar insights agregados sin ad_id
    if not ad_id:
        # Crear ad_id virtual para datos agregados de cuenta
        account_id = job.get("account_id", "unknown")
        date_start = ins.get("date_start", "unknown")
        date_stop = ins.get("date_stop", "unknown")
        publisher = ins.get("publisher_platform", "mixed")
        
        # Generar ad_id único pero determinístico para evitar duplicados
        ad_id = f"AGG_{account_id}_{date_start}_{date_stop}_{publisher}"
    
    row['ad_id'] = ad_id

    # 2) publisher_platform defensivo (sin breakdowns puede venir vacío)
    _pub = ins.get('publisher_platform')
    ALLOWED_PLATFORMS = {'facebook', 'instagram', 'messenger', 'audience_network'}
    if not _pub:
        row['publisher_platform'] = 'mixed'
    else:
        _pub_l = str(_pub).lower()
        row['publisher_platform'] = _pub_l if _pub_l in ALLOWED_PLATFORMS else 'mixed'

    # Helpers locales
    def num(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    def numint(x):
        try:
            return int(float(x))
        except Exception:
            return 0

    def sum_actions_field(field):
        # field puede ser una lista de {action_type,value} o un número/string
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

    # Actions parsing (legacy 'actions' list)
    actions = ins.get("actions") or []
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

    # Also check for action_values (newer API format)
    action_values = ins.get("action_values") or []
    if isinstance(action_values, list):
        for a in action_values:
            k = a.get("action_type")
            v = a.get("value")
            if k and k not in actions_dict:  # Don't overwrite existing
                try:
                    actions_dict[k] = float(v)
                except Exception:
                    actions_dict[k] = 0.0

    # Also check for conversions (another possible field)
    conversions = ins.get("conversions") or []
    if isinstance(conversions, list):
        for c in conversions:
            k = c.get("action_type")
            v = c.get("value")
            if k and k not in actions_dict:  # Don't overwrite existing
                try:
                    actions_dict[k] = float(v)
                except Exception:
                    actions_dict[k] = 0.0

    # DEBUG (silenciado por defecto)
    _DBG = os.getenv("META_SYNC_DEBUG", "0") == "1"
    if _DBG:
        ad_id = ins.get("ad_id", "unknown")
        messaging_action_keys = [k for k in actions_dict.keys() if "messaging" in k.lower() or "message" in k.lower()]
        if messaging_action_keys:
            print(f"📱 MESSAGING DEBUG - Ad {clean_surrogates(str(ad_id))}: Found messaging actions: {messaging_action_keys}")
            for key in messaging_action_keys:
                print(f"   {key}: {actions_dict[key]}")
        elif actions_dict:
            print(f"📱 MESSAGING DEBUG - Ad {clean_surrogates(str(ad_id))}: No messaging actions found. Available actions: {list(actions_dict.keys())}")
        else:
            print(f"📱 MESSAGING DEBUG - Ad {clean_surrogates(str(ad_id))}: No actions at all in this insight")

    # Video play actions (list)
    vpa = ins.get("video_play_actions") or []
    vpa_total = sum_actions_field(vpa)

    # Per-metric video sums (fields may be numeric or list)
    thruplays = sum_actions_field(ins.get("video_thruplay_watched_actions"))
    video_p25 = sum_actions_field(ins.get("video_p25_watched_actions"))
    video_p50 = sum_actions_field(ins.get("video_p50_watched_actions"))
    video_p75 = sum_actions_field(ins.get("video_p75_watched_actions"))
    video_p100 = sum_actions_field(ins.get("video_p100_watched_actions"))
    video_30s = sum_actions_field(ins.get("video_30_sec_watched_actions"))

    impressions = numint(ins.get("impressions"))
    reach = numint(ins.get("reach"))
    clicks = numint(ins.get("clicks"))
    inline_link_clicks = numint(ins.get("inline_link_clicks"))
    # link_clicks estándar (DDL lo trae)
    link_clicks = numint(ins.get("link_clicks"))
    outbound_clicks = numint(ins.get("outbound_clicks"))

    spend = num(ins.get("spend"))

    # cost per inline may be provided by API or computed
    cost_per_inline = None
    try:
        if ins.get('cost_per_inline_link_click') is not None:
            cost_per_inline = num(ins.get('cost_per_inline_link_click'))
        elif inline_link_clicks > 0:
            cost_per_inline = spend / inline_link_clicks
    except Exception:
        cost_per_inline = None

    thruplay_rate = None
    try:
        if impressions and impressions > 0:
            thruplay_rate = thruplays / impressions
    except Exception:
        thruplay_rate = None

    # Build a row keeping existing keys and adding legacy columns for compatibility
    publisher = ins.get("publisher_platform") or 'mixed'

    # 🔧 Detectar si es insight agregado (sin campaign_id/adset_id)
    is_aggregated = not ins.get("campaign_id") and not ins.get("adset_id")
    
    row = {
        "ad_id": ad_id,  # Usar el ad_id procesado (real o virtual)
        "fecha_inicio": ins.get("date_start"),
        "fecha_fin": ins.get("date_stop"),
        "publisher_platform": (ins.get('publisher_platform') or 'mixed'),
        # Para insights agregados, usar valores por defecto
        "campana_id": ins.get("campaign_id") or (f"AGG_CAMPAIGN_{job['account_id']}" if is_aggregated else None),
        "conjunto_id": ins.get("adset_id") or (f"AGG_ADSET_{job['account_id']}" if is_aggregated else None),
        "id_cuenta_publicitaria": job["account_id"],
        "importe_gastado": spend,
        "impresiones": impressions,
        "alcance": reach,
        "clicks": clicks,
        "link_clicks": link_clicks,
        "inline_link_clicks": inline_link_clicks,
        "outbound_clicks": outbound_clicks,
        "ctr": num(ins.get("ctr")),
    "cpc": num(ins.get("cpc")),
    "cost_per_1k_impressions": num(ins.get("cpm")),
        "frequency": num(ins.get("frequency")),
        "website_ctr": num(ins.get("website_ctr")),
        "quality_ranking": ins.get("quality_ranking"),
        # costo directo por inline (si se pudo calcular)
        "cost_per_inline_link_click": (cost_per_inline if cost_per_inline is not None else None),
        # Video action metrics (current/raw)
    # Raw video actions (kept for audit) and normalized video metrics matching DDL
    "video_play_actions": vpa,
    "video_avg_time_watched_actions": num(ins.get("video_avg_time_watched_actions")),
    # Normalized video counts (legacy/DDL columns are set later in the legacy mapping below)
        "actions": actions,  # jsonb raw
        "fecha_sincronizacion": now,
        "fecha_ultima_actualizacion": now,
        # --- Legacy compatibility columns requested ---
        "unique_impressions": reach or 0,
        "unique_clicks": clicks or 0,
        "unique_inline_link_clicks": inline_link_clicks or 0,
    "unique_outbound_clicks": outbound_clicks or 0,
        "unique_ctr": num(ins.get("ctr")) or 0.0,
        "cost_per_unique_click": (num(ins.get("cpc")) if ins.get('cpc') is not None else (spend / clicks if clicks > 0 else 0.0)),
        "cost_per_unique_inline_link_click": (cost_per_inline if cost_per_inline is not None else 0.0),
        "thruplays": thruplays or 0,
        "thruplay_rate": (thruplays / impressions if impressions > 0 else 0.0),
        "video_plays": vpa_total or 0,
        "video_plays_15s": thruplays or 0,
        "video_plays_at_25": video_p25 or 0,
        "video_plays_at_50": video_p50 or 0,
        "video_plays_at_75": video_p75 or 0,
        "video_plays_at_100": video_p100 or 0,
        # extras del DDL que conviene poblar si vienen
        "unique_link_clicks": numint(ins.get("unique_link_clicks") or 0),
        "objetivo_campana": ins.get("objective"),
        "status": ins.get("ad_status"),
    }

    # platform / publisher
    # Cuando no pedimos breakdowns, Graph no devuelve publisher_platform.
    # Estándar: caer en 'mixed' para no forzar 'facebook'.
    row['publisher_platform'] = (ins.get('publisher_platform') or 'mixed').lower()

    # DEBUG: Log all available actions for this insight
    if _DBG:
        print(f"🔍 ACTIONS AVAILABLE - Ad {clean_surrogates(str(ad_id))}: {list(actions_dict.keys())}")

    # Map → "mensajes iniciados" con prioridad canónica (mismas reglas que en meta_ads_sync_all.py)
    messaging_actions = [
        # 1) Preferidas (started)
        "onsite_conversion.messaging_conversation_started",
        "onsite_conversion.messaging_conversation_started_7d",
        # 2) Alternativas sin prefijo
        "messaging_conversation_started",
        "messaging_conversation_started_7d",
        # 3) Conexiones totales (aprox.)
        "onsite_conversion.total_messaging_connection",
        "total_messaging_connection",
        # 4) Último recurso
        "onsite_conversion.messaging_first_reply",
        "messaging_first_reply",
        # 5) Legacy/ambiguo
        "onsite_conversion.total_messaging",
    ]

    # Initialize messaging_conversations_started to 0 by default
    row["messaging_conversations_started"] = 0
    mapped_action = None

    for action_key in messaging_actions:
        if action_key in actions_dict:
            row["messaging_conversations_started"] = int(actions_dict[action_key])
            mapped_action = action_key
            if _DBG:
                print(f"📱 MESSAGING MAPPED - Ad {clean_surrogates(str(ad_id))}: {action_key} -> {row['messaging_conversations_started']} mensajes")
            break  # Use the first available one

    # Populate campaign/adset/ad name using cached helper to avoid rate limits
    try:
        nombre_nora = job.get('nombre_nora', '')
        if isinstance(nombre_nora, str) and nombre_nora:
            access_token = _resolver_token_meta(nombre_nora)
        else:
            access_token = None
    except Exception:
        access_token = None
    try:
        names = get_names_cached(ad_id, access_token)
    except Exception:
        names = {"campaign_name": None, "adset_name": None, "ad_name": None, "status": None}

    # 🔧 Nombres para insights agregados vs individuales
    if is_aggregated:
        row['nombre_anuncio'] = f"Agregado Cuenta {job['account_id']} ({publisher})"
        row['nombre_campana'] = f"Datos Agregados - Cuenta {job['account_id']}"
        row['nombre_conjunto'] = f"Conjunto Agregado - {publisher.title()}"
    else:
        # nombre_anuncio: prefer insight, then cached ad name
        row['nombre_anuncio'] = ins.get('ad_name') or names.get('ad_name') or str(ad_id)
        # nombre_campana / nombre_conjunto
        row['nombre_campana'] = ins.get('campaign_name') or names.get('campaign_name')
        row['nombre_conjunto'] = ins.get('adset_name') or names.get('adset_name')
    # status campaña/conjunto: preferir insight si viene; si no, usar cache Graph
    row['status_campana'] = (
        ins.get('campaign_status')
        or ins.get('campaign_effective_status')
        or names.get('campaign_status')
    )
    row['status_conjunto'] = (
        ins.get('adset_status')
        or ins.get('adset_effective_status')
        or names.get('adset_status')
    )

    # Compute unified messaging metrics (prefer SDK if possible)
    sdk_kpis = None
    # 🔧 MEJORADO: SDK con mejor error handling y logging
    _DBG_MESSAGING = os.getenv("META_SYNC_DEBUG", "0") == "1" or _DBG
    
    try:
        if callable(init_business) and access_token:
            try:
                init_business(access_token=access_token)
                if _DBG_MESSAGING:
                    print(f"💬 (SDK init) Inicializado FB SDK para ad_id={ad_id}")
            except Exception as sdk_init_err:
                if _DBG_MESSAGING:
                    print(f"⚠️ (SDK init) Error inicializando FB SDK: {sdk_init_err}")
        
        # TEMPORAL: Desactivar insights_mensajes para debug
        if False and callable(insights_mensajes) and access_token:
            try:
                # CRÍTICO: No tocar ins, usar copias para evitar mutación
                original_ins_type = type(ins)
                
                # Validar que ins sea un dict para obtener fechas
                if isinstance(ins, dict):
                    date_start = ins.get('date_start', '2024-01-01')
                    date_stop = ins.get('date_stop', '2024-12-31')
                else:
                    # Si ins ya no es dict aquí, algo lo modificó antes
                    if _DBG_MESSAGING:
                        print(f"⚠️ (SDK fecha) ad_id={ad_id} → ins cambió a {type(ins)} (era {original_ins_type})")
                    date_start = '2024-01-01'
                    date_stop = '2024-12-31'
                
                # Asegurar que las fechas sean strings
                date_start = str(date_start) if date_start else '2024-01-01'
                date_stop = str(date_stop) if date_stop else '2024-12-31'
                
                # Usar la firma original de insights_mensajes
                sdk_res = insights_mensajes(
                    scope='ad',
                    ids=[ad_id],
                    since=date_start,
                    until=date_stop,
                    time_increment='1',
                    retry=1,
                    nombre_nora=job.get('nombre_nora') or "",
                    empresa_id="",
                )
                
                # Verificar si ins sigue siendo dict después de la llamada
                if not isinstance(ins, dict) and _DBG_MESSAGING:
                    print(f"⚠️ (SDK mutación) ad_id={ad_id} → ins mutado por insights_mensajes: {type(ins)}")
                
                if sdk_res and isinstance(sdk_res, dict):
                    sdk_kpis = sdk_res.get(str(ad_id)) or sdk_res
                    if _DBG_MESSAGING and sdk_kpis:
                        print(f"💬 (SDK success) ad_id={ad_id} → SDK data keys: {list(sdk_kpis.keys()) if isinstance(sdk_kpis, dict) else type(sdk_kpis)}")
                else:
                    sdk_kpis = None
                    if _DBG_MESSAGING:
                        print(f"⚠️ (SDK empty) ad_id={ad_id} → No SDK data returned")
                        
            except Exception as sdk_call_err:
                sdk_kpis = None
                if _DBG_MESSAGING:
                    print(f"⚠️ (SDK error) ad_id={ad_id} → Error calling insights_mensajes: {sdk_call_err}")
        else:
            sdk_kpis = None
            if _DBG_MESSAGING and not access_token:
                print(f"⚠️ (SDK skip) ad_id={ad_id} → No access_token available")
            elif _DBG_MESSAGING:
                print(f"⚠️ (SDK skip) ad_id={ad_id} → insights_mensajes not callable")
    except Exception as sdk_outer_err:
        sdk_kpis = None
        if _DBG_MESSAGING:
            print(f"⚠️ (SDK outer) ad_id={ad_id} → Outer SDK error: {sdk_outer_err}")

    metrics = compute_messaging_metrics(ins, sdk_kpis, actions_dict, spend)

    # 💬 DEBUG MESSAGING específico (similar a meta_ads_sync_all.py)
    _DBG_MESSAGING = os.getenv("META_SYNC_DEBUG", "0") == "1" or _DBG
    if _DBG_MESSAGING:
        ms_final = int(metrics.get('messaging_conversations_started') or 0)
        ms_source = metrics.get('messages_source', 'unknown')
        cost_per_msg = metrics.get('cost_per_message')
        print(f"💬 (sincronizador) ad_id={ad_id} → ms={ms_final}, spend={spend}, cost_per_msg={cost_per_msg}, source={ms_source}")
        if ms_final == 0:
            print(f"⚠️ (sincronizador) ad_id={ad_id} → No messaging data found! spend={spend}, insight keys: {list(ins.keys())}")

    # Add new messaging columns only if allowed
    row['messaging_conversations_started'] = int(metrics.get('messaging_conversations_started') or 0)
    # Costo oficial de insights (si viene)
    try:
        _cpmcs_val = ins.get('cost_per_messaging_conversation_started')
        if _cpmcs_val is not None:
            row['cost_per_messaging_conversation_started'] = float(_cpmcs_val)
    except Exception:
        pass
    # Indicar fuente de mensajes (sdk | insight | derived)
    try:
        row['messages_source'] = metrics.get('messages_source')
    except Exception:
        row['messages_source'] = None

    # 🔧 TEMPORAL: Forzar guardado de columnas messaging (siempre, sin depender de HAS_NEW_MSG_COLS)
    if True:  # HAS_NEW_MSG_COLS:
        row['messaging_first_reply'] = int(metrics.get('messaging_first_reply') or 0)
        # safe float casts
        def _float_or_none(v):
            try:
                return float(v) if v is not None else None
            except Exception:
                return None
        row['cost_per_message'] = _float_or_none(metrics.get('cost_per_message'))
        row['mensajes_total'] = int(metrics.get('mensajes_total') or 0)
        row['costo_por_mensaje_total'] = _float_or_none(metrics.get('costo_por_mensaje_total'))
        row['msg_cost_is_calculated'] = bool(metrics.get('msg_cost_is_calculated') or False)
        # Also persist messages_source when writing the new message columns
        row['messages_source'] = metrics.get('messages_source')

    # DEBUG: Always log the final messaging value and what was mapped
    if _DBG:
        if mapped_action:
            print(f"📱 MESSAGING FINAL - Ad {ad_id}: messaging_conversations_started = {row['messaging_conversations_started']} (mapped from {mapped_action})")
        else:
            print(f"📱 MESSAGING FINAL - Ad {ad_id}: messaging_conversations_started = {row['messaging_conversations_started']} (no mapping found)")

    # Agregar nombre_nora para filtrado por tenant
    row['nombre_nora'] = job.get('nombre_nora', '')

    # Filtrar a columnas del DDL (y nuevas si habilitadas)
    try:
        row = {k: v for k, v in row.items() if k in ALLOWED_COLUMNS}
    except Exception:
        pass

    return row


def generar_reporte_para_cuenta(nombre_nora: str, cuenta_id: str, fecha_inicio: str, fecha_fin: str):
    """
    Genera un reporte agregado por cuenta similar a `meta_ads_reportes_semanales` y lo inserta.
    Sigue las reglas: usa `nombre_nora` en consultas, archive el previo activo y reusa public_token si existe.
    """
    empresa_id = None
    empresa_nombre = None
    try:
        cta_res = supabase.table("meta_ads_cuentas") \
            .select("empresa_id") \
            .eq("id_cuenta_publicitaria", cuenta_id) \
            .eq("nombre_nora", nombre_nora) \
            .single().execute()
        cta = (getattr(cta_res, 'data', None) or {})
        empresa_id = cta.get("empresa_id")
        if empresa_id:
            emp_res = supabase.table("cliente_empresas").select("nombre_empresa").eq("id", empresa_id).single().execute()
            emp = (getattr(emp_res, 'data', None) or {})
            empresa_nombre = emp.get("nombre_empresa")
    except Exception:
        pass

    # traer anuncios que solapan el rango
    try:
        print(f"[DEBUG] Buscando anuncios con parámetros:")
        print(f"  - nombre_nora: {clean_surrogates(nombre_nora)}")
        print(f"  - cuenta_id: {cuenta_id}")
        print(f"  - fecha_inicio: {fecha_inicio}")
        print(f"  - fecha_fin: {fecha_fin}")
        
        # Primero verificar si hay anuncios para este nombre_nora sin filtros de cuenta
        total_anuncios_nora = supabase.table("meta_ads_anuncios_detalle") \
            .select("id_cuenta_publicitaria, fecha_inicio, fecha_fin") \
            .eq("nombre_nora", nombre_nora) \
            .execute().data or []
        
        print(f"[DEBUG] Total anuncios para nora '{clean_surrogates(nombre_nora)}': {len(total_anuncios_nora)}")
        
        # Verificar anuncios para esta cuenta específica
        anuncios_cuenta = supabase.table("meta_ads_anuncios_detalle") \
            .select("id_cuenta_publicitaria, fecha_inicio, fecha_fin") \
            .eq("nombre_nora", nombre_nora) \
            .eq("id_cuenta_publicitaria", cuenta_id) \
            .execute().data or []
        
        print(f"[DEBUG] Anuncios para cuenta {cuenta_id}: {len(anuncios_cuenta)}")
        if anuncios_cuenta:
            print(f"[DEBUG] Primeros 3 registros encontrados:")
            for i, a in enumerate(anuncios_cuenta[:3]):
                print(f"  {i+1}. Cuenta: {a.get('id_cuenta_publicitaria')} | Fechas: {a.get('fecha_inicio')} → {a.get('fecha_fin')}")
        
        # Consulta con condiciones más permisivas para debug
        anuncios_debug = supabase.table("meta_ads_anuncios_detalle") \
            .select("fecha_inicio, fecha_fin, ad_id, id_cuenta_publicitaria") \
            .eq("nombre_nora", nombre_nora) \
            .eq("id_cuenta_publicitaria", cuenta_id) \
            .execute().data or []
            
        print(f"[DEBUG] Todos los anuncios de la cuenta: {len(anuncios_debug)}")
        if anuncios_debug:
            sample = anuncios_debug[0]
            print(f"[DEBUG] Sample record: fecha_inicio={sample.get('fecha_inicio')}, fecha_fin={sample.get('fecha_fin')}")
        
        anuncios = supabase.table("meta_ads_anuncios_detalle") \
            .select("*") \
            .eq("nombre_nora", nombre_nora) \
            .eq("id_cuenta_publicitaria", cuenta_id) \
            .gte("fecha_fin", fecha_inicio) \
            .lte("fecha_inicio", fecha_fin) \
            .execute().data or []
            
        print(f"[DEBUG] Anuncios en el rango {fecha_inicio} → {fecha_fin}: {len(anuncios)}")
        
        # Si no encuentra, probar con overlap logic más permisivo
        if not anuncios:
            anuncios_overlap = supabase.table("meta_ads_anuncios_detalle") \
                .select("*") \
                .eq("nombre_nora", nombre_nora) \
                .eq("id_cuenta_publicitaria", cuenta_id) \
                .execute().data or []
            
            # Filtro manual para debug
            anuncios_manual = []
            for a in anuncios_overlap:
                f_inicio = a.get('fecha_inicio')
                f_fin = a.get('fecha_fin')
                if f_inicio and f_fin:
                    if f_inicio <= fecha_fin and f_fin >= fecha_inicio:
                        anuncios_manual.append(a)
            
            print(f"[DEBUG] Anuncios con overlap manual: {len(anuncios_manual)}")
            anuncios = anuncios_manual
        
    except Exception as e:
        print(f"[DEBUG] Error en consulta de anuncios: {e}")
        anuncios = []

    if not anuncios:
        return {"ok": False, "msg": f"Sin datos de anuncios en el rango. Cuenta: {cuenta_id}, Rango: {fecha_inicio}-{fecha_fin}, Total en BD: {len(anuncios_cuenta) if 'anuncios_cuenta' in locals() else 'N/A'}"}

    fb = [a for a in anuncios if (a.get("publisher_platform") or "").lower() == "facebook"]
    ig = [a for a in anuncios if (a.get("publisher_platform") or "").lower() == "instagram"]

    def _i(x, k): return int(x.get(k, 0) or 0)
    def _f(x, k): return float(x.get(k, 0) or 0)

    total_imp = sum(_i(a, "impresiones") for a in anuncios)
    total_clicks = sum(_i(a, "clicks") for a in anuncios)
    total_spend = sum(_f(a, "importe_gastado") for a in anuncios)
    
    # 🆕 ANÁLISIS DE TIPOS DE INTERACCIONES Y RENDIMIENTO POR CAMPAÑA
    tipos_mensajes = {}
    objetivos_campana = {}
    
    # Analizar patrones de rendimiento y agrupación por campañas
    campanas_performance = {}
    
    for anuncio in anuncios:
        # Análisis por campaña (más útil que objetivos vacíos)
        campana_nombre = anuncio.get("nombre_campana", "Sin nombre")
        if campana_nombre not in campanas_performance:
            campanas_performance[campana_nombre] = {
                'anuncios': 0,
                'gasto_total': 0,
                'impresiones': 0,
                'clicks': 0,
                'mensajes': 0,
                'interacciones': 0
            }
        
        # Acumular métricas por campaña
        campanas_performance[campana_nombre]['anuncios'] += 1
        campanas_performance[campana_nombre]['gasto_total'] += _f(anuncio, "importe_gastado")
        campanas_performance[campana_nombre]['impresiones'] += _f(anuncio, "impresiones")
        campanas_performance[campana_nombre]['clicks'] += _f(anuncio, "clicks")
        campanas_performance[campana_nombre]['mensajes'] += _f(anuncio, "mensajes_total")
        campanas_performance[campana_nombre]['interacciones'] += _f(anuncio, "interacciones")
    
    # Generar análisis útil basado en resultados reales
    for campana, data in campanas_performance.items():
        # Clasificar por resultados concretos y útiles
        if data['mensajes'] > 50:  # Buena generación de mensajes
            categoria = "ALTA_CONVERSACIÓN"
        elif data['clicks'] > 1000:  # Alto volumen de clics
            categoria = "ALTO_TRÁFICO"
        elif data['impresiones'] > 50000:  # Gran alcance
            categoria = "GRAN_ALCANCE"
        elif data['interacciones'] > 500:  # Buen engagement
            categoria = "BUEN_ENGAGEMENT"
        else:
            categoria = "RENDIMIENTO_BÁSICO"
            
        if categoria in objetivos_campana:
            objetivos_campana[categoria] += data['anuncios']
        else:
            objetivos_campana[categoria] = data['anuncios']
    
    # Análisis de resultados y costos reales
    total_mensajes = sum(_i(a, "mensajes_total") for a in anuncios)
    total_clicks = sum(_i(a, "clicks") for a in anuncios)
    total_interacciones = sum(_i(a, "interacciones") for a in anuncios)
    total_link_clicks = sum(_i(a, "link_clicks") for a in anuncios)
    total_video_views = sum(_i(a, "video_views") for a in anuncios)
    
    # Calcular costos reales
    costo_por_mensaje = round(total_spend / total_mensajes, 2) if total_mensajes > 0 else 0
    costo_por_click = round(total_spend / total_clicks, 2) if total_clicks > 0 else 0
    costo_por_mil_impresiones = round((total_spend / total_imp) * 1000, 2) if total_imp > 0 else 0
    
    if total_mensajes > 0:
        tipos_mensajes["mensajes_directos"] = int(total_mensajes)
        tipos_mensajes["costo_por_mensaje"] = costo_por_mensaje
    if total_clicks > 0:
        tipos_mensajes["clicks_generales"] = int(total_clicks)
        tipos_mensajes["costo_por_click"] = costo_por_click
    if total_link_clicks > 0:
        tipos_mensajes["clicks_enlaces"] = int(total_link_clicks)
    if total_interacciones > 0:
        tipos_mensajes["interacciones_sociales"] = int(total_interacciones)
    if total_video_views > 0:
        tipos_mensajes["reproducciones_video"] = int(total_video_views)
    if total_imp > 0:
        tipos_mensajes["impresiones_totales"] = int(total_imp)
        tipos_mensajes["cpm"] = costo_por_mil_impresiones

    reporte = {
        "empresa_id": empresa_id,
        "id_cuenta_publicitaria": cuenta_id,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total_campañas": len({a.get("campana_id") for a in anuncios if a.get("campana_id")}),
        "importe_gastado_campañas": total_spend,
        "total_conjuntos": len({a.get("conjunto_id") for a in anuncios if a.get("conjunto_id")}),
        "importe_gastado_conjuntos": total_spend,
        "total_anuncios": len({a.get("ad_id") for a in anuncios if a.get("ad_id")}),
        "importe_gastado_anuncios": total_spend,
        "impresiones": int(total_imp),
        "alcance": sum(_i(a, "alcance") for a in anuncios),
        "clicks": int(total_clicks),
        "link_clicks": sum(_i(a, "link_clicks") for a in anuncios) or sum(_i(a, "inline_link_clicks") for a in anuncios),
        "mensajes": sum(_i(a, "messaging_conversations_started") for a in anuncios),
        "interacciones": sum(_i(a, "page_engagement") for a in anuncios) or sum(_i(a, "post_engagement") for a in anuncios) or sum(_i(a, "post_engagements") for a in anuncios),
        "video_plays": sum(_i(a, "video_plays") for a in anuncios),
        "reproducciones_video_3s": sum(_i(a, "reproducciones_video_3s") for a in anuncios),

        "facebook_impresiones": sum(_i(a, "impresiones") for a in fb),
        "facebook_alcance": sum(_i(a, "alcance") for a in fb),
        "facebook_clicks": sum(_i(a, "clicks") for a in fb),
        "facebook_mensajes": sum(_i(a, "messaging_conversations_started") for a in fb),
        "facebook_importe_gastado": sum(_f(a, "importe_gastado") for a in fb),

        "instagram_impresiones": sum(_i(a, "impresiones") for a in ig),
        "instagram_alcance": sum(_i(a, "alcance") for a in ig),
        "instagram_clicks": sum(_i(a, "clicks") for a in ig),
        "instagram_mensajes": sum(_i(a, "messaging_conversations_started") for a in ig),
        "instagram_importe_gastado": sum(_f(a, "importe_gastado") for a in ig),

        "empresa_nombre": empresa_nombre,
        "nombre_nora": nombre_nora,
        "estatus": "activo",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "public_token": None,
        
        # 🆕 NUEVOS CAMPOS: Análisis de mensajes y objetivos
        "tipos_mensajes_json": tipos_mensajes,
        "objetivos_campanas_json": objetivos_campana,
    }

    # --- Fallback robusto si mensajes quedaron en 0 (detalle histórico o mapeo incompleto) ---
    try:
        if int(reporte.get("mensajes") or 0) == 0:
            def _msgs_from_actions(rows):
                total = 0
                for r in rows:
                    acts = r.get("actions") or []
                    if not isinstance(acts, list):
                        continue
                    # normaliza a dict {action_type -> float}
                    adict = {}
                    for a in acts:
                        k = (a or {}).get("action_type")
                        v = (a or {}).get("value")
                        if not k:
                            continue
                        try:
                            # Proteger contra None/valores no convertibles y fallback a 0.0
                            if v is None:
                                adict[k] = 0.0
                            else:
                                adict[k] = float(v)
                        except Exception:
                            # Si no se puede convertir, asegurar valor numérico por defecto
                            try:
                                adict[k] = float(str(v))
                            except Exception:
                                adict[k] = 0.0
                    # misma prioridad que arriba
                    for key in (
                        "onsite_conversion.messaging_conversation_started",
                        "onsite_conversion.messaging_conversation_started_7d",
                        "messaging_conversation_started",
                        "messaging_conversation_started_7d",
                        "onsite_conversion.total_messaging_connection",
                        "total_messaging_connection",
                        "onsite_conversion.messaging_first_reply",
                        "messaging_first_reply",
                        "onsite_conversion.total_messaging",
                    ):
                        if key in adict:
                            try:
                                total += int(adict[key])
                            except Exception:
                                total += int(float(adict[key]) if adict[key] not in (None, "") else 0)
                            break
                return total

            total_msgs = _msgs_from_actions(anuncios)
            fb_msgs    = _msgs_from_actions([a for a in anuncios if (a.get("publisher_platform") or "").lower() == "facebook"])
            ig_msgs    = _msgs_from_actions([a for a in anuncios if (a.get("publisher_platform") or "").lower() == "instagram"])

            reporte["mensajes"] = total_msgs
            reporte["facebook_mensajes"] = fb_msgs
            reporte["instagram_mensajes"] = ig_msgs
    except Exception:
        # no romper inserción de reporte por fallback
        pass

    # KPI base para insights_json (CTR/CPC)
    ctr = (total_clicks / total_imp) if total_imp else 0.0
    cpc = (total_spend / total_clicks) if total_clicks else 0.0
    try:
        reporte_for_insights = {
            "ctr": ctr,
            "cpc": cpc,
            "frecuencia": None,
            "impresiones": total_imp,
            "clicks": total_clicks,
            "importe_gastado_anuncios": total_spend,
        }
        reporte_insights = construir_insights_json(reporte_for_insights)
        reporte["insights_json"] = reporte_insights
    except Exception:
        reporte["insights_json"] = {}

    # Idempotencia: archivar previo activo si existe
    try:
        # Primero verificar si ya existe un reporte activo para estos parámetros
        existing_report = supabase.table("meta_ads_reportes_semanales") \
            .select("id, public_token") \
            .eq("empresa_id", empresa_id) \
            .eq("id_cuenta_publicitaria", cuenta_id) \
            .eq("fecha_inicio", fecha_inicio) \
            .eq("fecha_fin", fecha_fin) \
            .eq("estatus", "activo") \
            .eq("nombre_nora", nombre_nora) \
            .execute().data

        if existing_report:
            # Si ya existe un reporte activo, archivarlo
            supabase.table("meta_ads_reportes_semanales") \
                .update({"estatus": "archivado", "archivado_en": datetime.now(timezone.utc).isoformat()}) \
                .eq("id", existing_report[0]["id"]) \
                .execute()
    except Exception as e:
        # Si hay error en el archivado, continuar con la inserción
        pass

    # Siempre generar un nuevo token único para evitar conflictos
    reporte["public_token"] = str(uuid.uuid4())

    # Remover campos calculados temporales si existen
    for c in ("ctr", "cpc"):
        if c in reporte: del reporte[c]

    # Insertar reporte (filtrar campos no existentes en la tabla)
    try:
        from clientes.aura.utils.supabase_schemas import SUPABASE_SCHEMAS
        valid_columns = set(SUPABASE_SCHEMAS.get('meta_ads_reportes_semanales', {}).keys())
        # Ensure nombre_nora is present for multi-tenant filtering
        reporte["nombre_nora"] = nombre_nora
        # ⚠️ Diagnóstico: si el esquema no incluye 'mensajes' (o facebook_/instagram_), avisa en logs
        _missing = [k for k in ("mensajes","facebook_mensajes","instagram_mensajes") if k not in valid_columns]
        if _missing:
            logging.warning(f"[meta_ads_reportes_semanales] columnas ausentes en schema, se omitirán: {_missing}")
            # Intenta fallback: si 'mensajes' no está, pero existe 'total_mensajes' en el schema, mapea ahí
            if "mensajes" not in valid_columns and "total_mensajes" in valid_columns:
                reporte["total_mensajes"] = reporte.get("mensajes", 0)
        
        # 🆕 Asegurar nuevas columnas JSON aunque no estén en el schema estático
        _json_analysis_keys = {"tipos_mensajes_json", "objetivos_campanas_json"}
        _missing_json = [k for k in _json_analysis_keys if k not in valid_columns]
        if _missing_json:
            print(f"[DEBUG] Columnas JSON ausentes en schema estático, agregándolas: {_missing_json}")
            # Expandimos valid_columns para incluir las nuevas columnas JSON
            valid_columns = valid_columns.union(_json_analysis_keys)
        
        # Asegurar columnas de mensajes aunque no estén en el schema estático
        _mensajes_keys = {"mensajes", "facebook_mensajes", "instagram_mensajes"}
        if not _mensajes_keys.issubset(valid_columns):
            # (opcional) fallback si tu UI esperaba 'total_mensajes'
            if "mensajes" not in valid_columns and "total_mensajes" in valid_columns and "mensajes" in reporte:
                reporte["total_mensajes"] = reporte.get("mensajes", 0)
            # Expandimos temporalmente valid_columns para permitir inserción si queremos conservar las claves
            valid_columns = valid_columns.union(_mensajes_keys)
        # Construir payload final solo con columnas válidas (evita errores PostgREST)
        reporte_bd = {k: v for k, v in reporte.items() if k in valid_columns}
        
        # Debug: log de parámetros de inserción
        print(f"[DEBUG] Insertando reporte - nombre_nora: {clean_surrogates(nombre_nora)}, cuenta: {cuenta_id}, fechas: {fecha_inicio} → {fecha_fin}, estatus: {reporte_bd.get('estatus')}")
        print(f"[DEBUG] Campos del reporte: {list(reporte_bd.keys())}")
        
        result = supabase.table("meta_ads_reportes_semanales").insert(reporte_bd).execute()
        
        # Debug: confirmar inserción
        if result.data:
            print(f"[DEBUG] Reporte insertado exitosamente - ID: {result.data[0].get('id') if result.data else 'N/A'}")
        else:
            print(f"[DEBUG] Inserción completada pero sin datos de retorno")
            
    except Exception as e:
        print(f"[DEBUG] Error en inserción de reporte: {e}")
        raise

    return {"ok": True, "reporte": {"empresa_id": empresa_id, "cuenta": cuenta_id, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin, "public_token": reporte["public_token"]}}

@sincronizador_personalizado_bp.route("/historial")
def obtener_historial(nombre_nora=None):
    """Obtiene historial de sincronizaciones"""
    try:
        nombre_nora = require_nombre_nora(allow_path_fallback=True)
        q_acc  = request.args.get("account_id")
        q_from = request.args.get("date_from")
        q_to   = request.args.get("date_to")
        tenant_jobs = [job for job in sync_jobs.values() if job.get('nombre_nora') == nombre_nora]
        if q_acc:
            tenant_jobs = [j for j in tenant_jobs if j.get("account_id") == q_acc]
        if q_from:
            tenant_jobs = [j for j in tenant_jobs if (j.get("date_from") or "") >= q_from]
        if q_to:
            tenant_jobs = [j for j in tenant_jobs if (j.get("date_to") or "") <= q_to]
        # Ordenar por fecha de inicio (más recientes primero)
        tenant_jobs.sort(
            key=lambda x: x.get('started_at', ''),
            reverse=True
        )
        runs = []
        for jid, job in [(j.get("job_id"), j) for j in tenant_jobs[:20]]:
            item = {
                "job_id": jid,
                "status": job.get("status"),
                "account_id": job.get("account_id"),
                "date_from": job.get("date_from"),
                "date_to": job.get("date_to"),
                "modo": job.get("modo"),
                "processed": job.get("processed"),
                "total": job.get("total"),
                "started_at": job.get("started_at"),
                "finished_at": job.get("finished_at"),
                "errors": _normalize_errors(job.get("errors")),
                "message": job.get("message")  # ← NUEVO: para que el historial tenga el texto que pintas en el <pre>
            }
            if item["errors"]:
                item["error_summary"] = "; ".join(item["errors"])[:200]
            runs.append(item)

        # ¿CSV?
        want_csv = (request.args.get("format") == "csv") or ("text/csv" in (request.headers.get("Accept") or ""))
        if want_csv:
            out = io.StringIO()
            writer = csv.writer(out)
            header = ["job_id","status","account_id","date_from","date_to","modo","processed","total","started_at","finished_at","errors"]
            writer.writerow(header)
            for j in tenant_jobs:
                errs = j.get("errors")
                if isinstance(errs, list):
                    err_txt = "; ".join(str(x) for x in errs)
                elif errs:
                    err_txt = str(errs)
                else:
                    err_txt = ""
                writer.writerow([
                    j.get("job_id"),
                    j.get("status"),
                    j.get("account_id"),
                    j.get("date_from"),
                    j.get("date_to"),
                    j.get("modo"),
                    j.get("processed"),
                    j.get("total"),
                    j.get("started_at"),
                    j.get("finished_at"),
                    err_txt,
                ])
            csv_bytes = out.getvalue().encode("utf-8")
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"historial_{nombre_nora}_{ts}.csv"
            return Response(
                csv_bytes,
                mimetype="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        return jsonify({
            "runs": runs
        })
    except Exception as e:
        logging.error(f"Error obteniendo historial: {e}")
        return jsonify({
            "error": {
                "code": "HISTORY_ERROR",
                "message": f"Error obteniendo historial: {str(e)}"
            }
        }), 500

