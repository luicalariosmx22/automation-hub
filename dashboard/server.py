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
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
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
supabase = None


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
    return send_file('jobs-manager-local.html')


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Obtiene todos los jobs configurados."""
    try:
        result = supabase.table("jobs_config").select("*").order("job_name").execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Error obteniendo jobs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/pending', methods=['GET'])
def get_pending_jobs():
    """Obtiene jobs pendientes de ejecución."""
    try:
        jobs = fetch_jobs_pendientes(supabase)
        return jsonify({"success": True, "data": jobs})
    except Exception as e:
        logger.error(f"Error obteniendo jobs pendientes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/<job_name>', methods=['GET'])
def get_job(job_name):
    """Obtiene configuración de un job específico."""
    try:
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
    try:
        data = request.json
        enabled = data.get('enabled', True)
        habilitar_deshabilitar_job(supabase, job_name, enabled)
        return jsonify({"success": True, "message": f"Job {job_name} {'habilitado' if enabled else 'deshabilitado'}"})
    except Exception as e:
        logger.error(f"Error toggling job {job_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/jobs/<job_name>/interval', methods=['POST'])
def update_interval(job_name):
    """Actualiza el intervalo de ejecución de un job."""
    try:
        data = request.json
        interval = data.get('interval_minutes')
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
    try:
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


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Crea un nuevo job."""
    try:
        data = request.json
        job_name = data.get('job_name')
        interval = data.get('schedule_interval_minutes', 1440)
        
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


if __name__ == '__main__':
    print("🚀 Dashboard de Jobs corriendo en http://localhost:5000")
    print("📊 Credenciales cargadas desde .env automáticamente")
    print("")
    app.run(debug=True, port=5000, host='0.0.0.0')
