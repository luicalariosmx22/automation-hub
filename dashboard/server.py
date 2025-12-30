"""
Servidor local para el dashboard de jobs.
Lee credenciales del .env y expone API REST.

Uso:
    PYTHONPATH=src python dashboard/server.py
    
Luego abre http://localhost:5000
"""
import os
import logging
from datetime import datetime
from typing import Optional
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from supabase import Client
from automation_hub.config.logging import setup_logging
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.jobs_config_repo import (
    fetch_jobs_pendientes,
    marcar_job_ejecutado,
    get_job_config,
    actualizar_intervalo,
    habilitar_deshabilitar_job
)

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Cliente Supabase global
supabase: Optional[Client] = None


@app.before_request
def init_supabase():
    """Inicializa cliente Supabase si no existe."""
    global supabase
    if supabase is None:
        try:
            supabase = create_client_from_env()
            logger.info("Cliente Supabase inicializado")
        except Exception as e:
            logger.error(f"Error inicializando Supabase: {e}")


@app.route('/')
def index():
    """Sirve el dashboard HTML."""
    return send_file('jobs-dashboard.html')


@app.route('/notifications-manager.html')
def notifications_manager():
    """Sirve el gestor de notificaciones."""
    return send_file('notifications-manager.html')


@app.route('/telegram-system.html')
def telegram_system():
    """Sirve el sistema completo de Telegram."""
    return send_file('telegram-system.html')


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Obtiene todos los jobs configurados."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("jobs_config").select("*").order("job_name").execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error obteniendo jobs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/pending', methods=['GET'])
def get_pending_jobs():
    """Obtiene jobs pendientes de ejecución."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        jobs = fetch_jobs_pendientes(supabase)
        return jsonify({"success": True, "data": jobs})
    except Exception as e:
        logger.error(f"Error obteniendo jobs pendientes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/<job_name>', methods=['GET'])
def get_job(job_name):
    """Obtiene configuración de un job específico."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        job = get_job_config(supabase, job_name)
        if job:
            return jsonify({"success": True, "data": job})
        return jsonify({"success": False, "error": "Job no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error obteniendo job {job_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/<job_name>/toggle', methods=['POST'])
def toggle_job(job_name):
    """Habilita o deshabilita un job."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        enabled = data.get('enabled', True) if data else True
        habilitar_deshabilitar_job(supabase, job_name, enabled)
        return jsonify({"success": True, "message": f"Job {job_name} {'habilitado' if enabled else 'deshabilitado'}"})
    except Exception as e:
        logger.error(f"Error toggling job {job_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/<job_name>/interval', methods=['POST'])
def update_interval(job_name):
    """Actualiza el intervalo de ejecución de un job."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        interval = data.get('interval_minutes') if data else None
        if not interval or not isinstance(interval, int):
            return jsonify({"success": False, "error": "interval_minutes requerido"}), 400
        
        actualizar_intervalo(supabase, job_name, interval)
        return jsonify({"success": True, "message": f"Intervalo actualizado a {interval} minutos"})
    except Exception as e:
        logger.error(f"Error actualizando intervalo de {job_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/<job_name>/run-now', methods=['POST'])
def run_now(job_name):
    """Programa un job para ejecutarse inmediatamente."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = (
            supabase.table("jobs_config")
            .update({
                "next_run_at": datetime.utcnow().isoformat(),
                "enabled": True
            })
            .eq("job_name", job_name)
            .execute()
        )
        
        if result.data:
            return jsonify({"success": True, "message": f"Job {job_name} programado para ejecutarse ahora"})
        return jsonify({"success": False, "error": "Job no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error programando job {job_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/<job_name>/run', methods=['POST'])
def run_job(job_name):
    """Ejecuta un job manualmente de forma síncrona."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        # Importar el registry dinámicamente
        from automation_hub.jobs import registry
        
        # Buscar el job en el registry usando get_job()
        job_func = registry.get_job(job_name)
        if not job_func:
            available_jobs = registry.list_jobs()
            return jsonify({
                "success": False, 
                "error": f"Job '{job_name}' no encontrado. Jobs disponibles: {', '.join(available_jobs)}"
            }), 404
        
        # Ejecutar el job
        logger.info(f"Ejecutando manualmente job: {job_name}")
        job_func()
        
        # Actualizar last_run_at y next_run_at
        assert supabase is not None
        job_config = get_job_config(supabase, job_name)
        if job_config:
            interval_mins = job_config.get('schedule_interval_minutes', 1440)
            from datetime import timedelta
            next_run = datetime.utcnow() + timedelta(minutes=interval_mins)
            
            supabase.table("jobs_config").update({
                "last_run_at": datetime.utcnow().isoformat(),
                "next_run_at": next_run.isoformat()
            }).eq("job_name", job_name).execute()
        
        return jsonify({"success": True, "message": f"Job {job_name} ejecutado exitosamente"})
    except Exception as e:
        logger.error(f"Error ejecutando job {job_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Crea un nuevo job."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        job_name = data.get('job_name') if data else None
        interval = data.get('schedule_interval_minutes', 1440) if data else 1440
        
        if not job_name:
            return jsonify({"success": False, "error": "job_name requerido"}), 400
        
        result = (
            supabase.table("jobs_config")
            .insert({
                "job_name": job_name,
                "enabled": True,
                "schedule_interval_minutes": interval,
                "next_run_at": datetime.utcnow().isoformat()
            })
            .execute()
        )
        
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error creando job: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({
        "success": True,
        "status": "healthy",
        "supabase_connected": supabase is not None
    })


# ==========================================
# NOTIFICACIONES TELEGRAM ENDPOINTS
# ==========================================

@app.route('/api/notifications/contacts', methods=['GET'])
def get_notification_contacts():
    """Obtiene todos los contactos de notificaciones."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("notificaciones_telegram_config").select("*").order("nombre_nora, nombre_contacto").execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error obteniendo contactos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications/contacts/<int:contact_id>', methods=['GET'])
def get_notification_contact(contact_id):
    """Obtiene un contacto específico."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("notificaciones_telegram_config").select("*").eq("id", contact_id).execute()
        if result.data:
            return jsonify({"success": True, "data": result.data[0]})
        return jsonify({"success": False, "error": "Contacto no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error obteniendo contacto {contact_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications/contacts', methods=['POST'])
def create_notification_contact():
    """Crea un nuevo contacto de notificaciones."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        
        if not data or not data.get('nombre_nora') or not data.get('chat_id'):
            return jsonify({"success": False, "error": "nombre_nora y chat_id son requeridos"}), 400
        
        insert_data = {
            "nombre_nora": data['nombre_nora'],
            "chat_id": data['chat_id'],
            "nombre_contacto": data.get('nombre_contacto'),
            "jobs_permitidos": data.get('jobs_permitidos'),
            "prioridades_permitidas": data.get('prioridades_permitidas'),
            "tipos_alerta_permitidos": data.get('tipos_alerta_permitidos'),
            "activo": data.get('activo', True),
            "notas": data.get('notas')
        }
        
        result = supabase.table("notificaciones_telegram_config").insert(insert_data).execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error creando contacto: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications/contacts/<int:contact_id>', methods=['PUT'])
def update_notification_contact(contact_id):
    """Actualiza un contacto de notificaciones."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        
        if not data:
            return jsonify({"success": False, "error": "Datos requeridos"}), 400
        
        update_data = {}
        for field in ['nombre_nora', 'chat_id', 'nombre_contacto', 'jobs_permitidos', 
                      'prioridades_permitidas', 'tipos_alerta_permitidos', 'activo', 'notas']:
            if field in data:
                update_data[field] = data[field]
        
        result = supabase.table("notificaciones_telegram_config").update(update_data).eq("id", contact_id).execute()
        
        if result.data:
            return jsonify({"success": True, "data": result.data})
        return jsonify({"success": False, "error": "Contacto no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error actualizando contacto {contact_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications/contacts/<int:contact_id>/toggle', methods=['POST'])
def toggle_notification_contact(contact_id):
    """Activa o desactiva un contacto."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        activo = data.get('activo', True) if data else True
        
        result = supabase.table("notificaciones_telegram_config").update({"activo": activo}).eq("id", contact_id).execute()
        
        if result.data:
            return jsonify({"success": True, "message": f"Contacto {'activado' if activo else 'desactivado'}"})
        return jsonify({"success": False, "error": "Contacto no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error toggling contacto {contact_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications/contacts/<int:contact_id>', methods=['DELETE'])
def delete_notification_contact(contact_id):
    """Elimina un contacto de notificaciones."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("notificaciones_telegram_config").delete().eq("id", contact_id).execute()
        
        if result.data:
            return jsonify({"success": True, "message": "Contacto eliminado"})
        return jsonify({"success": False, "error": "Contacto no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error eliminando contacto {contact_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# TELEGRAM SYSTEM ENDPOINTS
# ==========================================

@app.route('/api/telegram/bots', methods=['GET'])
def get_telegram_bots():
    """Obtiene todos los bots de Telegram."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("telegram_bots").select("*").order("nombre").execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error obteniendo bots: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/bots/<int:bot_id>', methods=['GET'])
def get_telegram_bot(bot_id):
    """Obtiene un bot específico."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("telegram_bots").select("*").eq("id", bot_id).execute()
        if result.data:
            return jsonify({"success": True, "data": result.data[0]})
        return jsonify({"success": False, "error": "Bot no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error obteniendo bot {bot_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/bots', methods=['POST'])
def create_telegram_bot():
    """Crea un nuevo bot de Telegram."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        
        if not data or not data.get('nombre') or not data.get('token'):
            return jsonify({"success": False, "error": "nombre y token son requeridos"}), 400
        
        insert_data = {
            "nombre": data['nombre'],
            "token": data['token'],
            "descripcion": data.get('descripcion'),
            "activo": data.get('activo', True)
        }
        
        result = supabase.table("telegram_bots").insert(insert_data).execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error creando bot: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/bots/<int:bot_id>', methods=['PUT'])
def update_telegram_bot(bot_id):
    """Actualiza un bot de Telegram."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        
        update_data = {}
        for field in ['nombre', 'token', 'descripcion', 'activo']:
            if field in data:
                update_data[field] = data[field]
        
        result = supabase.table("telegram_bots").update(update_data).eq("id", bot_id).execute()
        
        if result.data:
            return jsonify({"success": True, "data": result.data})
        return jsonify({"success": False, "error": "Bot no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error actualizando bot {bot_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/bots/<int:bot_id>', methods=['DELETE'])
def delete_telegram_bot(bot_id):
    """Elimina un bot de Telegram."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("telegram_bots").delete().eq("id", bot_id).execute()
        
        if result.data:
            return jsonify({"success": True, "message": "Bot eliminado"})
        return jsonify({"success": False, "error": "Bot no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error eliminando bot {bot_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/bots/<int:bot_id>/test', methods=['POST'])
def test_telegram_bot(bot_id):
    """Envía un mensaje de prueba con un bot."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        chat_id = data.get('chat_id') if data else None
        
        if not chat_id:
            return jsonify({"success": False, "error": "chat_id requerido"}), 400
        
        # Obtener bot
        bot_result = supabase.table("telegram_bots").select("*").eq("id", bot_id).execute()
        if not bot_result.data:
            return jsonify({"success": False, "error": "Bot no encontrado"}), 404
        
        bot = bot_result.data[0]
        
        # Enviar mensaje de prueba
        import requests
        url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"🧪 Mensaje de prueba del bot: {bot['nombre']}\n\n✅ Bot funcionando correctamente!",
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        # Guardar en historial
        supabase.table("telegram_historial").insert({
            "bot_id": bot_id,
            "chat_id": chat_id,
            "mensaje": payload['text'],
            "tipo_alerta": "test",
            "prioridad": "baja",
            "estado": "enviado"
        }).execute()
        
        return jsonify({"success": True, "message": "Mensaje de prueba enviado"})
    except Exception as e:
        logger.error(f"Error probando bot {bot_id}: {e}")
        
        # Guardar error en historial
        try:
            supabase.table("telegram_historial").insert({
                "bot_id": bot_id,
                "chat_id": chat_id,
                "mensaje": "Mensaje de prueba",
                "tipo_alerta": "test",
                "prioridad": "baja",
                "estado": "error",
                "error": str(e)
            }).execute()
        except:
            pass
        
        return jsonify({"success": False, "error": str(e)}), 500


# Templates endpoints
@app.route('/api/telegram/templates', methods=['GET'])
def get_telegram_templates():
    """Obtiene todos los templates de mensajes."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("telegram_message_templates").select("*").order("nombre").execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error obteniendo templates: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/templates/<int:template_id>', methods=['GET'])
def get_telegram_template(template_id):
    """Obtiene un template específico."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("telegram_message_templates").select("*").eq("id", template_id).execute()
        if result.data:
            return jsonify({"success": True, "data": result.data[0]})
        return jsonify({"success": False, "error": "Template no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error obteniendo template {template_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/templates', methods=['POST'])
def create_telegram_template():
    """Crea un nuevo template de mensaje."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        
        if not data or not data.get('nombre') or not data.get('tipo_alerta') or not data.get('mensaje'):
            return jsonify({"success": False, "error": "nombre, tipo_alerta y mensaje son requeridos"}), 400
        
        insert_data = {
            "nombre": data['nombre'],
            "tipo_alerta": data['tipo_alerta'],
            "mensaje": data['mensaje'],
            "prioridad": data.get('prioridad', 'media'),
            "activo": data.get('activo', True)
        }
        
        result = supabase.table("telegram_message_templates").insert(insert_data).execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error creando template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/templates/<int:template_id>', methods=['PUT'])
def update_telegram_template(template_id):
    """Actualiza un template de mensaje."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        data = request.json
        
        update_data = {}
        for field in ['nombre', 'tipo_alerta', 'mensaje', 'prioridad', 'activo']:
            if field in data:
                update_data[field] = data[field]
        
        result = supabase.table("telegram_message_templates").update(update_data).eq("id", template_id).execute()
        
        if result.data:
            return jsonify({"success": True, "data": result.data})
        return jsonify({"success": False, "error": "Template no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error actualizando template {template_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/telegram/templates/<int:template_id>', methods=['DELETE'])
def delete_telegram_template(template_id):
    """Elimina un template de mensaje."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        result = supabase.table("telegram_message_templates").delete().eq("id", template_id).execute()
        
        if result.data:
            return jsonify({"success": True, "message": "Template eliminado"})
        return jsonify({"success": False, "error": "Template no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error eliminando template {template_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Historial endpoints
@app.route('/api/telegram/historial', methods=['GET'])
def get_telegram_historial():
    """Obtiene el historial de notificaciones enviadas."""
    if supabase is None:
        return jsonify({"success": False, "error": "Supabase no conectado"}), 500
    
    try:
        assert supabase is not None
        
        # Parámetros de filtro
        bot_id = request.args.get('bot_id')
        estado = request.args.get('estado')
        limit = int(request.args.get('limit', 50))
        
        query = (
            supabase.table("telegram_historial")
            .select("*, bot:bot_id(nombre)")
            .order("created_at", desc=True)
            .limit(limit)
        )
        
        if bot_id:
            query = query.eq("bot_id", bot_id)
        if estado:
            query = query.eq("estado", estado)
        
        result = query.execute()
        
        # Formatear datos
        historial = []
        for item in result.data:
            bot_nombre = item.get('bot', {}).get('nombre', 'Desconocido') if isinstance(item.get('bot'), dict) else 'Desconocido'
            historial.append({
                **item,
                'bot_nombre': bot_nombre
            })
        
        return jsonify({"success": True, "data": historial})
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("🚀 Dashboard de Jobs corriendo en http://localhost:5000")
    print("📊 Credenciales cargadas desde .env automáticamente")
    print("")
    app.run(debug=True, port=5000, host='0.0.0.0')
