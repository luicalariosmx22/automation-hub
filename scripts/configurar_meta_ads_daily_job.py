#!/usr/bin/env python3
"""
Script para configurar el job de Meta Ads Daily Sync
Configura el job para ejecutarse diariamente a las 1 AM

Uso:
    PYTHONPATH=src python scripts/configurar_meta_ads_daily_job.py
"""

import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio src al PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from automation_hub.config.logging import setup_logging
from automation_hub.db.supabase_client import create_client_from_env
import logging

logger = logging.getLogger(__name__)

def configurar_job_meta_ads_daily():
    """Configura el job de Meta Ads Daily Sync en la tabla jobs_config"""
    
    # Inicializar logging
    setup_logging()
    logger.info("🚀 Configurando Meta Ads Daily Sync Job")
    
    # Conectar a Supabase
    supabase = create_client_from_env()
    
    # Configuración del job
    job_config = {
        "job_name": "meta_ads_daily_sync",
        "enabled": True,
        "schedule_interval_minutes": 1440,  # 24 horas
        "config": {
            "descripcion": "Sincroniza diariamente datos de anuncios de Meta Ads del día anterior",
            "horario": "1:00 AM",
            "cron_expression": "0 1 * * *",
            "tabla_destino": "meta_ads_anuncios_daily",
            "dependencias": [
                "SUPABASE_URL", 
                "SUPABASE_KEY", 
                "META_ADS_ACCESS_TOKEN"
            ]
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Verificar si ya existe
        existing_job = supabase.table('jobs_config') \
            .select('*') \
            .eq('job_name', job_config['job_name']) \
            .execute()
        
        if existing_job.data:
            logger.info("📝 Job existente encontrado, actualizando...")
            
            # Actualizar job existente
            result = supabase.table('jobs_config') \
                .update({
                    'enabled': job_config['enabled'],
                    'schedule_interval_minutes': job_config['schedule_interval_minutes'],
                    'config': job_config['config'],
                    'updated_at': job_config['updated_at']
                }) \
                .eq('job_name', job_config['job_name']) \
                .execute()
                
            logger.info("✅ Job actualizado correctamente")
            
        else:
            logger.info("➕ Creando nuevo job...")
            
            # Crear nuevo job
            result = supabase.table('jobs_config') \
                .insert(job_config) \
                .execute()
                
            logger.info("✅ Job creado correctamente")
        
        # Verificar configuración
        verificar_job = supabase.table('jobs_config') \
            .select('*') \
            .eq('job_name', 'meta_ads_daily_sync') \
            .execute()
        
        if verificar_job.data:
            job = verificar_job.data[0]
            logger.info("="*60)
            logger.info("📊 CONFIGURACIÓN DEL JOB")
            logger.info("="*60)
            logger.info(f"🔹 Nombre: {job['job_name']}")
            logger.info(f"🔹 Habilitado: {job['enabled']}")
            logger.info(f"🔹 Intervalo: {job['schedule_interval_minutes']} minutos (24 horas)")
            logger.info(f"🔹 Horario: 1:00 AM todos los días")
            logger.info(f"🔹 Descripción: {job['config'].get('descripcion', 'N/A')}")
            logger.info(f"🔹 Tabla destino: {job['config'].get('tabla_destino', 'N/A')}")
            logger.info("="*60)
        
        logger.info("🎉 ¡Configuración completada exitosamente!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error configurando job: {e}")
        return False

if __name__ == "__main__":
    success = configurar_job_meta_ads_daily()
    if success:
        print("✅ Job configurado correctamente")
    else:
        print("❌ Error en la configuración")
        sys.exit(1)