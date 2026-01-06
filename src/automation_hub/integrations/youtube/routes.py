"""
Rutas web para OAuth de YouTube
"""
from flask import Blueprint, request, redirect, jsonify, render_template_string, url_for
import logging
import os
from automation_hub.integrations.youtube.youtube_service import YouTubeService
from automation_hub.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Blueprint para rutas de YouTube
youtube_bp = Blueprint('youtube', __name__, url_prefix='/integraciones/youtube')

def get_youtube_service():
    """Helper para obtener servicio de YouTube"""
    supabase = get_supabase_client()
    client_secrets = os.getenv('YOUTUBE_CLIENT_SECRETS_FILE', 'youtube_client_secrets.json')
    return YouTubeService(supabase, client_secrets)

@youtube_bp.route('/connect')
def connect():
    """
    Inicia flujo OAuth para conectar canal de YouTube
    
    Query params:
        - cliente_id: ID del cliente que quiere conectar
    
    Redirige al usuario a la página de autorización de Google
    """
    cliente_id = request.args.get('cliente_id')
    
    if not cliente_id:
        return jsonify({
            'error': 'Se requiere cliente_id'
        }), 400
    
    try:
        youtube_service = get_youtube_service()
        
        # Generar redirect_uri dinámicamente
        redirect_uri = url_for('youtube.callback', _external=True)
        
        # Obtener URL de autorización
        auth_url = youtube_service.get_authorization_url(
            cliente_id=cliente_id,
            redirect_uri=redirect_uri
        )
        
        logger.info(f"Redirigiendo cliente {cliente_id} a OAuth de YouTube")
        
        # Mostrar warning antes de redirigir
        warning_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Conectar YouTube</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .warning-box {{
                    background: #fff3cd;
                    border: 2px solid #ffc107;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                .warning-box h2 {{
                    color: #856404;
                    margin-top: 0;
                }}
                .warning-box p {{
                    color: #856404;
                    line-height: 1.6;
                }}
                .continue-btn {{
                    background: #007bff;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                }}
                .continue-btn:hover {{
                    background: #0056b3;
                }}
            </style>
        </head>
        <body>
            <div class="warning-box">
                <h2>⚠️ Importante: Permisos de YouTube</h2>
                <p>
                    <strong>Solo el OWNER (propietario) del canal puede conectar YouTube.</strong>
                </p>
                <p>
                    Si tienes permisos de <strong>Manager</strong> o <strong>Editor</strong> en YouTube Studio,
                    <strong>NO podrás</strong> usar esta integración. Los permisos de Studio no funcionan con YouTube APIs.
                </p>
                <p>
                    Debes iniciar sesión con la cuenta de Google que es <strong>propietaria del canal</strong>.
                </p>
            </div>
            
            <a href="{auth_url}" class="continue-btn">
                Entiendo, continuar con Google
            </a>
        </body>
        </html>
        """
        
        return warning_html
        
    except Exception as e:
        logger.error(f"Error iniciando OAuth: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@youtube_bp.route('/callback')
def callback():
    """
    Maneja el callback de OAuth de Google
    
    Query params:
        - code: Código de autorización
        - state: cliente_id original
    """
    code = request.args.get('code')
    state = request.args.get('state')  # cliente_id
    error = request.args.get('error')
    
    if error:
        return jsonify({
            'error': f'OAuth cancelado: {error}'
        }), 400
    
    if not code or not state:
        return jsonify({
            'error': 'Parámetros inválidos'
        }), 400
    
    cliente_id = state
    
    try:
        youtube_service = get_youtube_service()
        
        # Generar redirect_uri (debe coincidir con el del flow)
        redirect_uri = url_for('youtube.callback', _external=True)
        
        # Intercambiar código por tokens y obtener canal_id
        conexion = youtube_service.handle_oauth_callback(
            code=code,
            cliente_id=cliente_id,
            redirect_uri=redirect_uri
        )
        
        logger.info(
            f"Cliente {cliente_id} conectó canal: "
            f"{conexion['canal_titulo']} ({conexion['canal_id']})"
        )
        
        # Página de éxito
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>YouTube Conectado</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .success-box {{
                    background: #d4edda;
                    border: 2px solid #28a745;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                }}
                .success-box h2 {{
                    color: #155724;
                    margin-top: 0;
                }}
                .success-box p {{
                    color: #155724;
                    font-size: 18px;
                }}
                .canal-info {{
                    background: white;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .canal-info strong {{
                    display: block;
                    margin-bottom: 5px;
                }}
                .close-btn {{
                    background: #28a745;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="success-box">
                <h2>✅ ¡YouTube conectado exitosamente!</h2>
                
                <div class="canal-info">
                    <strong>Canal conectado:</strong>
                    {conexion['canal_titulo']}
                    <br><br>
                    <strong>ID del canal:</strong>
                    <code>{conexion['canal_id']}</code>
                </div>
                
                <p>Ahora puedes subir videos a YouTube Shorts automáticamente.</p>
                
                <button class="close-btn" onclick="window.close()">
                    Cerrar ventana
                </button>
            </div>
        </body>
        </html>
        """
        
        return success_html
        
    except Exception as e:
        logger.error(f"Error en callback OAuth: {str(e)}")
        
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .error-box {{
                    background: #f8d7da;
                    border: 2px solid #dc3545;
                    border-radius: 8px;
                    padding: 20px;
                }}
                .error-box h2 {{
                    color: #721c24;
                    margin-top: 0;
                }}
                .error-box p {{
                    color: #721c24;
                }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h2>❌ Error al conectar YouTube</h2>
                <p>{str(e)}</p>
                <p>
                    <strong>Posibles causas:</strong>
                    <ul>
                        <li>No eres el OWNER del canal (solo manager/editor)</li>
                        <li>No autorizaste todos los permisos requeridos</li>
                        <li>Error de configuración en las credenciales</li>
                    </ul>
                </p>
            </div>
        </body>
        </html>
        """
        
        return error_html, 500

@youtube_bp.route('/disconnect/<conexion_id>', methods=['POST'])
def disconnect(conexion_id):
    """
    Desconecta un canal de YouTube
    
    Args:
        conexion_id: ID de la conexión a eliminar
    """
    try:
        youtube_service = get_youtube_service()
        youtube_service.disconnect_youtube(conexion_id)
        
        return jsonify({
            'success': True,
            'message': 'Canal desconectado'
        })
        
    except Exception as e:
        logger.error(f"Error desconectando YouTube: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@youtube_bp.route('/canales/<cliente_id>')
def list_canales(cliente_id):
    """
    Lista canales conectados de un cliente
    
    Args:
        cliente_id: ID del cliente
    """
    try:
        youtube_service = get_youtube_service()
        canales = youtube_service.get_canales_conectados(cliente_id)
        
        return jsonify({
            'success': True,
            'canales': canales
        })
        
    except Exception as e:
        logger.error(f"Error listando canales: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500
