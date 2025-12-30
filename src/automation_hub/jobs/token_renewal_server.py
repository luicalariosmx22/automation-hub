"""
Servidor Flask para renovar tokens de Google OAuth automáticamente
Recibe el callback de Google y actualiza el .env
"""
import os
import logging
import json
from datetime import datetime
from flask import Flask, request, redirect, jsonify
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv, set_key
import secrets

load_dotenv()
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Puerto para el servidor de renovación
RENEWAL_PORT = 5555

# Archivo de log de renovaciones
RENEWALS_LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.token_renewals.json')

def log_renewal(service_name: str, refresh_token: str, success: bool = True, error_msg: str = None):
    """Registra una renovación de token en el archivo de log"""
    try:
        # Crear archivo si no existe
        log_path = os.path.abspath(RENEWALS_LOG_FILE)
        
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"renovaciones": []}
        
        # Agregar nueva renovación
        renewal_entry = {
            "servicio": service_name,
            "fecha": datetime.now().isoformat(),
            "fecha_legible": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "token_preview": refresh_token[:30] + "..." if refresh_token else None,
            "exito": success,
            "error": error_msg
        }
        
        data["renovaciones"].append(renewal_entry)
        
        # Guardar (mantener solo últimas 100 renovaciones)
        data["renovaciones"] = data["renovaciones"][-100:]
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Renovación registrada: {service_name} - {success}")
        
    except Exception as e:
        logger.error(f"Error registrando renovación: {e}")

def get_last_renewal(service_name: str):
    """Obtiene la última renovación de un servicio"""
    try:
        log_path = os.path.abspath(RENEWALS_LOG_FILE)
        
        if not os.path.exists(log_path):
            return None
        
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Buscar última renovación exitosa del servicio
        for renewal in reversed(data["renovaciones"]):
            if renewal["servicio"] == service_name and renewal["exito"]:
                return renewal
        
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo última renovación: {e}")
        return None

def get_gbp_flow():
    """Crea el flow OAuth para GBP"""
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"http://127.0.0.1:{RENEWAL_PORT}/oauth/gbp/callback"]
        }
    }
    
    scopes = [
        "https://www.googleapis.com/auth/business.manage",
        "https://www.googleapis.com/auth/plus.business.manage"
    ]
    
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=f"http://127.0.0.1:{RENEWAL_PORT}/oauth/gbp/callback"
    )
    
    return flow

def get_calendar_flow():
    """Crea el flow OAuth para Google Calendar"""
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"http://127.0.0.1:{RENEWAL_PORT}/oauth/calendar/callback"]
        }
    }
    
    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
    ]
    
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=f"http://127.0.0.1:{RENEWAL_PORT}/oauth/calendar/callback"
    )
    
    return flow

@app.route('/renew/gbp')
def renew_gbp():
    """Inicia el flujo de renovación para GBP"""
    try:
        flow = get_gbp_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',  # Forzar consent para obtener nuevo refresh token
            include_granted_scopes='true'
        )
        
        # Guardar state en sesión (simple, sin BD)
        app.config['oauth_state'] = state
        
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error iniciando renovación GBP: {e}")
        return f"❌ Error: {e}", 500

@app.route('/renew/calendar')
def renew_calendar():
    """Inicia el flujo de renovación para Calendar"""
    try:
        flow = get_calendar_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        
        app.config['oauth_state'] = state
        
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error iniciando renovación Calendar: {e}")
        return f"❌ Error: {e}", 500

@app.route('/oauth/gbp/callback')
def oauth_gbp_callback():
    """Callback de Google OAuth para GBP - Actualiza .env automáticamente"""
    try:
        flow = get_gbp_flow()
        flow.fetch_token(code=request.args.get('code'))
        
        credentials = flow.credentials
        refresh_token = credentials.refresh_token
        
        if not refresh_token:
            log_renewal("GBP", None, success=False, error_msg="No refresh token obtenido")
            return "❌ No se obtuvo refresh token. Intenta revocar acceso en https://myaccount.google.com/permissions y vuelve a intentar.", 400
        
        # Actualizar .env
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env')
        env_path = os.path.abspath(env_path)
        
        set_key(env_path, "GBP_REFRESH_TOKEN", refresh_token)
        
        # Registrar renovación exitosa
        log_renewal("GBP", refresh_token, success=True)
        
        logger.info(f"✅ GBP_REFRESH_TOKEN actualizado exitosamente")
        
        return f"""
        <html>
        <head>
            <title>✅ Token Renovado</title>
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0; }}
                .success {{ background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #4CAF50; }}
                code {{ background: #f4f4f4; padding: 5px 10px; border-radius: 3px; }}
                .timestamp {{ color: #666; font-size: 14px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="success">
                <h1>✅ Token GBP Renovado</h1>
                <p>El token de <strong>Google Business Profile</strong> se actualizó correctamente en el archivo .env</p>
                <p><code>GBP_REFRESH_TOKEN</code> = {refresh_token[:50]}...</p>
                <div class="timestamp">
                    <p>🕒 Renovado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                <p>Puedes cerrar esta ventana.</p>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error en callback GBP: {e}")
        log_renewal("GBP", None, success=False, error_msg=str(e))
        return f"❌ Error: {e}", 500

@app.route('/oauth/calendar/callback')
def oauth_calendar_callback():
    """Callback de Google OAuth para Calendar - Actualiza .env automáticamente"""
    try:
        flow = get_calendar_flow()
        flow.fetch_token(code=request.args.get('code'))
        
        credentials = flow.credentials
        refresh_token = credentials.refresh_token
        
        if not refresh_token:
            log_renewal("Calendar", None, success=False, error_msg="No refresh token obtenido")
            return "❌ No se obtuvo refresh token. Intenta revocar acceso en https://myaccount.google.com/permissions y vuelve a intentar.", 400
        
        # Actualizar .env
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env')
        env_path = os.path.abspath(env_path)
        
        set_key(env_path, "GOOGLE_CALENDAR_REFRESH_TOKEN", refresh_token)
        
        # Registrar renovación exitosa
        log_renewal("Calendar", refresh_token, success=True)
        
        logger.info(f"✅ GOOGLE_CALENDAR_REFRESH_TOKEN actualizado exitosamente")
        
        return f"""
        <html>
        <head>
            <title>✅ Token Renovado</title>
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0; }}
                .success {{ background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #4CAF50; }}
                code {{ background: #f4f4f4; padding: 5px 10px; border-radius: 3px; }}
                .timestamp {{ color: #666; font-size: 14px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="success">
                <h1>✅ Token Calendar Renovado</h1>
                <p>El token de <strong>Google Calendar</strong> se actualizó correctamente en el archivo .env</p>
                <p><code>GOOGLE_CALENDAR_REFRESH_TOKEN</code> = {refresh_token[:50]}...</p>
                <div class="timestamp">
                    <p>🕒 Renovado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                <p>Puedes cerrar esta ventana.</p>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error en callback Calendar: {e}")
        log_renewal("Calendar", None, success=False, error_msg=str(e))
        return f"❌ Error: {e}", 500

@app.route('/health')
def health():
    """Health check"""
    return jsonify({"status": "ok", "service": "token_renewal_server"})

if __name__ == '__main__':
    print(f"""
    ╔════════════════════════════════════════════════════════════════╗
    ║  🔄 SERVIDOR DE RENOVACIÓN DE TOKENS GOOGLE OAUTH              ║
    ╚════════════════════════════════════════════════════════════════╝
    
    Servidor iniciado en: http://127.0.0.1:{RENEWAL_PORT}
    
    📍 URLs de Renovación:
    ┌────────────────────────────────────────────────────────────────┐
    │ GBP:      http://127.0.0.1:{RENEWAL_PORT}/renew/gbp            │
    │ Calendar: http://127.0.0.1:{RENEWAL_PORT}/renew/calendar       │
    └────────────────────────────────────────────────────────────────┘
    
    ⚡ Funcionamiento:
    1. Abre la URL en tu navegador
    2. Autoriza el acceso en Google
    3. El .env se actualiza automáticamente
    4. ✅ Listo!
    
    Presiona Ctrl+C para detener el servidor
    """)
    
    app.run(host='127.0.0.1', port=RENEWAL_PORT, debug=True)
