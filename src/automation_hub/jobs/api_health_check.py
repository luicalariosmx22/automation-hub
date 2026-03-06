"""
Job para verificar el estado de todos los tokens y APIs.

Verifica:
- OpenAI API
- DeepSeek API
- Gemini API
- Twilio (WhatsApp)
- Google OAuth (GBP)
- Meta/Facebook API
- Telegram Bot
- Supabase
- TikTok API
- Google Calendar API

Envía notificación por Telegram si algún servicio falla.
"""
import logging
import os
import json
from typing import Dict, List, Tuple
from datetime import datetime
import requests
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.meta_ads.token_resolver import resolve_meta_token, token_from_env

logger = logging.getLogger(__name__)

JOB_NAME = "api.health_check"

# Archivo de log de renovaciones
RENEWALS_LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.token_renewals.json')

def get_token_age(service_name: str) -> str:
    """Obtiene la antigüedad del token desde la última renovación"""
    try:
        log_path = os.path.abspath(RENEWALS_LOG_FILE)
        
        if not os.path.exists(log_path):
            return ""
        
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Buscar última renovación exitosa del servicio
        for renewal in reversed(data["renovaciones"]):
            if renewal["servicio"] == service_name and renewal["exito"]:
                renewal_date = datetime.fromisoformat(renewal["fecha"])
                days_old = (datetime.now() - renewal_date).days
                
                if days_old == 0:
                    return " (renovado hoy)"
                elif days_old == 1:
                    return " (1 día)"
                else:
                    return f" ({days_old} días)"
        
        return ""
        
    except Exception as e:
        logger.error(f"Error obteniendo antigüedad del token: {e}")
        return ""


def verificar_openai() -> Tuple[bool, str]:
    """Verifica que la API de OpenAI funcione."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return False, "API Key no configurada"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Verificar modelos disponibles
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "OK"
        elif response.status_code == 401:
            return False, "API Key inválida"
        else:
            return False, f"Error HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_deepseek() -> Tuple[bool, str]:
    """Verifica que la API de DeepSeek funcione."""
    try:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return False, "API Key no configurada"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Verificar con endpoint de modelos
        response = requests.get(
            "https://api.deepseek.com/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "OK"
        elif response.status_code == 401:
            return False, "API Key inválida"
        else:
            return False, f"Error HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_gemini() -> Tuple[bool, str]:
    """Verifica que la API de Gemini funcione."""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return False, "API Key no configurada"
        
        # Verificar con endpoint de modelos
        response = requests.get(
            f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "OK"
        elif response.status_code == 403:
            return False, "API Key inválida"
        else:
            return False, f"Error HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_google_oauth() -> Tuple[bool, str]:
    """Verifica que el refresh token de Google OAuth funcione."""
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_REDACTED_SECRET")
        refresh_token = os.getenv("GBP_REFRESH_TOKEN")
        
        if not all([client_id, client_secret, refresh_token]):
            return False, "Credenciales incompletas"
        
        if client_secret and "REDACTED" in client_secret:
            return False, "Client Secret es REDACTED"
        
        # Intentar refrescar token
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                age = get_token_age("GBP")
                return True, f"OK{age}"
            else:
                return False, "No se obtuvo access_token"
        elif response.status_code == 400:
            # Token expirado - incluir link de renovación
            age = get_token_age("GBP")
            return False, f"Token expirado{age} - Renovar: http://127.0.0.1:5555/renew/gbp"
        else:
            return False, f"Error HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_meta() -> Tuple[bool, str]:
    """Verifica que el token de Meta/Facebook funcione."""
    try:
        access_token = None
        token_source = None

        try:
            supabase = create_client_from_env()
            rows = (
                supabase.table("meta_tokens")
                .select("nombre_nora")
                .eq("provider", "meta")
                .eq("status", "active")
                .not_.is_("token", "null")
                .limit(200)
                .execute()
            )

            noras = sorted({r.get("nombre_nora") for r in (rows.data or []) if r.get("nombre_nora")})
            if "Sistema" in noras:
                noras.remove("Sistema")
                noras.insert(0, "Sistema")

            for nora in noras:
                token, source = resolve_meta_token(
                    supabase,
                    nora,
                    fallback_noras=[],
                    allow_env_fallback=False,
                )
                if token:
                    access_token = token
                    token_source = source
                    break
        except Exception as e:
            logger.warning(f"No se pudo resolver token de Meta desde BD para health check: {e}")

        if not access_token:
            access_token, token_source = token_from_env()

        if not access_token:
            return False, "Access token no configurado (ni en meta_tokens ni en env)"

        if "REDACTED" in access_token:
            return False, f"Token es REDACTED ({token_source or 'unknown'})"
        
        # Verificar token con debug
        response = requests.get(
            f"https://graph.facebook.com/v21.0/debug_token?input_token={access_token}&access_token={access_token}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data", {}).get("is_valid"):
                return True, f"OK ({token_source or 'unknown'})"
            else:
                return False, f"Token no válido ({token_source or 'unknown'})"
        elif response.status_code == 400:
            return False, f"Token inválido o expirado ({token_source or 'unknown'})"
        else:
            return False, f"Error HTTP {response.status_code} ({token_source or 'unknown'})"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_telegram() -> Tuple[bool, str]:
    """Verifica que el bot de Telegram funcione."""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not bot_token:
            return False, "Bot token no configurado"
        
        # Verificar bot
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_username = data.get("result", {}).get("username", "")
                return True, f"OK (@{bot_username})"
            else:
                return False, "Respuesta no válida"
        elif response.status_code == 401:
            return False, "Bot token inválido"
        else:
            return False, f"Error HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_supabase() -> Tuple[bool, str]:
    """Verifica que Supabase funcione."""
    try:
        from automation_hub.db.supabase_client import create_client_from_env
        
        supabase = create_client_from_env()
        
        # Hacer una query simple
        result = supabase.table("cliente_empresas").select("id").limit(1).execute()
        
        if result.data is not None:
            return True, "OK"
        else:
            return False, "No se pudo consultar la BD"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_tiktok() -> Tuple[bool, str]:
    """Verifica configuración de TikTok API."""
    try:
        client_key = os.getenv("TIKTOK_CLIENT_KEY")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
        
        if not client_key or not client_secret:
            return False, "Credenciales no configuradas"
        
        # Solo validar que existan (TikTok requiere OAuth flow completo)
        return True, "Credenciales configuradas"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_smtp_gmail() -> Tuple[bool, str]:
    """Verifica configuración de SMTP Gmail."""
    try:
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = os.getenv("SMTP_PORT")
        
        if not all([smtp_user, smtp_password, smtp_host, smtp_port]):
            return False, "Configuración incompleta"
        
        # Verificar que los valores sean correctos
        if smtp_host != "smtp.gmail.com":
            return False, f"Host incorrecto: {smtp_host}"
        
        if smtp_port not in ["587", "465"]:
            return False, f"Puerto incorrecto: {smtp_port}"
        
        # Solo validar que existan, no intentar conectar (puede bloquear)
        return True, "Credenciales configuradas"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_railway() -> Tuple[bool, str]:
    """Verifica configuración de Railway."""
    try:
        token = os.getenv("RAILWAY_TOKEN")
        project_id = os.getenv("RAILWAY_PROJECT_ID")
        service_id = os.getenv("RAILWAY_SERVICE_ID")
        
        if not all([token, project_id, service_id]):
            return False, "Configuración incompleta"
        
        # Validar que tengan formato correcto
        if not token or len(token) < 30:
            return False, "Token muy corto o vacío"
        
        return True, "Credenciales configuradas"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_meta_webhook() -> Tuple[bool, str]:
    """Verifica configuración de Meta Webhook."""
    try:
        verify_token = os.getenv("META_WEBHOOK_VERIFY_REDACTED_TOKEN")
        webhook_url = os.getenv("META_WEBHOOK_URL")
        webhook_secret = os.getenv("META_WEBHOOK_REDACTED_SECRET")
        
        if not all([verify_token, webhook_url, webhook_secret]):
            return False, "Configuración incompleta"
        
        if (verify_token and "REDACTED" in verify_token) or (webhook_secret and "REDACTED" in webhook_secret):
            return False, "Tokens son REDACTED"
        
        if webhook_url and not webhook_url.startswith("https://"):
            return False, "URL debe ser HTTPS"
        
        return True, "Configuración OK"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_meta_app() -> Tuple[bool, str]:
    """Verifica configuración de Meta App."""
    try:
        app_id = os.getenv("META_APP_ID")
        app_secret = os.getenv("META_APP_REDACTED_SECRET")
        
        if not all([app_id, app_secret]):
            return False, "Configuración incompleta"
        
        if app_secret and "REDACTED" in app_secret:
            return False, "App Secret es REDACTED"
        
        # Validar que app_id sea numérico
        if app_id and not app_id.isdigit():
            return False, "App ID inválido"
        
        return True, "Configuración OK"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_encryption_key() -> Tuple[bool, str]:
    """Verifica que exista la encryption key."""
    try:
        key = os.getenv("NORA_ENCRYPTION_KEY")
        
        if not key:
            return False, "Key no configurada"
        
        # Validar que tenga longitud apropiada para Fernet
        if len(key) < 40:
            return False, "Key muy corta"
        
        return True, "Key configurada"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def verificar_google_calendar() -> Tuple[bool, str]:
    """Verifica tokens de Google Calendar desde la tabla google_calendar_sync en Supabase."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from automation_hub.db.supabase_client import create_client_from_env
        
        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
        
        if not all([client_id, client_secret]):
            return False, "Credenciales OAuth incompletas"
        
        # Conectar a Supabase y obtener todos los tokens de usuarios
        supabase = create_client_from_env()
        response = supabase.table("google_calendar_sync").select("nombre_nora, refresh_token").execute()
        
        if not response.data:
            return True, "Sin calendarios conectados (OK)"
        
        tokens = response.data
        total = len(tokens)
        expirados = []
        validos = []
        
        # Verificar cada token
        for token_data in tokens:
            nombre = token_data.get("nombre_nora", "Desconocido")
            refresh_token = token_data.get("refresh_token")
            
            if not refresh_token or len(refresh_token) < 30:
                expirados.append(nombre)
                continue
            
            try:
                # Intentar refrescar token
                credentials = Credentials(
                    token=None,
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret
                )
                
                request = Request()
                credentials.refresh(request)
                
                if credentials.token:
                    validos.append(nombre)
                else:
                    expirados.append(nombre)
                    
            except Exception as e:
                if "invalid_grant" in str(e).lower():
                    expirados.append(nombre)
                else:
                    expirados.append(f"{nombre} (error)")
        
        # Reportar resultados
        if expirados:
            usuarios_exp = ", ".join(expirados)
            return False, f"⚠️ {len(expirados)}/{total} tokens expirados: {usuarios_exp}"
        else:
            return True, f"✅ {total} calendarios conectados OK"
            
    except Exception as e:
        error_str = str(e)
        return False, f"Error verificando: {error_str[:80]}"


def run(ctx=None):
    """
    Ejecuta la verificación de todos los servicios y envía reporte.
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Verificar todos los servicios
    verificaciones = {
        "OpenAI API": verificar_openai,
        "DeepSeek API": verificar_deepseek,
        "Gemini API": verificar_gemini,
        "Google OAuth (GBP)": verificar_google_oauth,
        "Google Calendar": verificar_google_calendar,
        "Meta/Facebook API": verificar_meta,
        "Meta App Config": verificar_meta_app,
        "Meta Webhook Config": verificar_meta_webhook,
        "Telegram Bot": verificar_telegram,
        "Supabase": verificar_supabase,
        "TikTok API": verificar_tiktok,
        "SMTP Gmail": verificar_smtp_gmail,
        "Railway Config": verificar_railway,
        "Encryption Key": verificar_encryption_key,
    }
    
    resultados = {}
    servicios_fallando = []
    
    logger.info(f"Verificando {len(verificaciones)} servicios...")
    
    for nombre_servicio, verificar_func in verificaciones.items():
        logger.info(f"Verificando {nombre_servicio}...")
        try:
            exitoso, mensaje = verificar_func()
            resultados[nombre_servicio] = {
                "exitoso": exitoso,
                "mensaje": mensaje
            }
            
            if not exitoso:
                servicios_fallando.append(nombre_servicio)
                logger.warning(f"❌ {nombre_servicio}: {mensaje}")
            else:
                logger.info(f"✓ {nombre_servicio}: {mensaje}")
                
        except Exception as e:
            resultados[nombre_servicio] = {
                "exitoso": False,
                "mensaje": f"Error inesperado: {str(e)}"
            }
            servicios_fallando.append(nombre_servicio)
            logger.error(f"❌ {nombre_servicio}: Error inesperado - {e}")
    
    # Preparar reporte
    total_servicios = len(verificaciones)
    servicios_ok = total_servicios - len(servicios_fallando)
    
    # Enviar notificación si hay fallos
    if servicios_fallando:
        logger.warning(f"⚠️ {len(servicios_fallando)} servicios fallando")
        
        try:
            from automation_hub.integrations.telegram.notifier import TelegramNotifier
            # Bot de Notificaciones
            telegram = TelegramNotifier(
                bot_token="8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE",
                default_chat_id="5674082622"
            )
            
            # Construir mensaje
            mensaje = f"🚨 <b>ALERTA: APIs/Tokens con Problemas</b>\n\n"
            mensaje += f"📊 Estado: {servicios_ok}/{total_servicios} servicios funcionando\n"
            mensaje += f"⏰ Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            mensaje += "❌ <b>Servicios fallando:</b>\n"
            for servicio in servicios_fallando:
                error_msg = resultados[servicio]["mensaje"]
                mensaje += f"\n• <b>{servicio}</b>\n  └ {error_msg}\n"
            
            # Servicios OK
            if servicios_ok > 0:
                mensaje += "\n✅ <b>Servicios funcionando:</b>\n"
                for nombre, info in resultados.items():
                    if info["exitoso"]:
                        mensaje += f"• {nombre}\n"
            
            telegram.enviar_mensaje(mensaje)
            logger.info("Notificación de fallo enviada por Telegram")
            
        except Exception as e:
            logger.error(f"Error enviando notificación de Telegram: {e}")
    else:
        logger.info(f"✅ Todos los servicios funcionando correctamente ({total_servicios}/{total_servicios})")
        
        # Enviar notificación de éxito (opcional, solo si quieres confirmación diaria)
        try:
            from automation_hub.integrations.telegram.notifier import TelegramNotifier
            # Bot de Notificaciones
            telegram = TelegramNotifier(
                bot_token="8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE",
                default_chat_id="5674082622"
            )
            
            mensaje = f"✅ <b>Health Check: Todo OK</b>\n\n"
            mensaje += f"📊 {total_servicios} servicios verificados\n"
            mensaje += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            mensaje += "Todos los tokens y APIs funcionan correctamente."
            
            telegram.enviar_mensaje(mensaje, disable_notification=True)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de éxito: {e}")
    
    return {
        "job": JOB_NAME,
        "timestamp": datetime.now().isoformat(),
        "total_servicios": total_servicios,
        "servicios_ok": servicios_ok,
        "servicios_fallando": len(servicios_fallando),
        "servicios_con_error": servicios_fallando,
        "resultados": resultados
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    resultado = run()
    print(f"\n{'='*60}")
    print(f"Resultado: {resultado['servicios_ok']}/{resultado['total_servicios']} servicios OK")
    if resultado['servicios_fallando'] > 0:
        print(f"⚠️ Servicios con problemas: {', '.join(resultado['servicios_con_error'])}")
    print(f"{'='*60}\n")
