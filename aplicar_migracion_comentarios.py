#!/usr/bin/env python3
"""
Script para aplicar la migración del job de automatización de comentarios
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def aplicar_migracion():
    """Aplica la migración para el job de automatización de comentarios"""
    from automation_hub.db.supabase_client import create_client_from_env
    
    print("🔧 Aplicando migración del job de automatización de comentarios...")
    
    supabase = create_client_from_env()
    
    # Leer el archivo SQL
    migration_file = "migrations/add_meta_comentarios_automation_job.sql"
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Extraer solo el INSERT (sin comentarios)
        lines = sql_content.split('\n')
        sql_lines = []
        in_insert = False
        
        for line in lines:
            if line.startswith('INSERT INTO'):
                in_insert = True
            if in_insert and not line.startswith('--'):
                sql_lines.append(line)
        
        sql_query = '\n'.join(sql_lines)
        
        # Ejecutar usando RPC para SQL raw
        result = supabase.rpc('execute_sql', {'sql_query': sql_query}).execute()
        
        print("✅ Migración aplicada exitosamente")
        print(f"📊 Resultado: {result}")
        
        # Verificar que el job se insertó
        job_check = supabase.table('jobs_config').select('*').eq('job_name', 'meta.comentarios.automation').execute()
        
        if job_check.data:
            job = job_check.data[0]
            print(f"🎯 Job configurado:")
            print(f"   - Nombre: {job['job_name']}")
            print(f"   - Habilitado: {job['enabled']}")
            print(f"   - Intervalo: {job['schedule_interval_minutes']} minutos")
            print(f"   - Creado: {job['created_at']}")
        else:
            print("⚠️ No se pudo verificar la inserción del job")
            
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo {migration_file}")
    except Exception as e:
        print(f"❌ Error aplicando migración: {e}")
        
        # Fallback: insertar manualmente
        try:
            print("🔄 Intentando inserción manual...")
            
            job_data = {
                'job_name': 'meta.comentarios.automation',
                'enabled': True,
                'schedule_interval_minutes': 5,
                'config': {
                    "description": "Automatización de comentarios de Meta (Facebook/Instagram) tipo ManyChat",
                    "features": [
                        "Detección de palabras clave en comentarios",
                        "Respuestas automáticas",
                        "Notificaciones al administrador",
                        "Alertas urgentes para comentarios negativos",
                        "Detección de leads calificados"
                    ],
                    "reglas_configuradas": 4,
                    "acciones_soportadas": [
                        "responder_automatico",
                        "notificar_admin", 
                        "alerta_urgente",
                        "lead_calificado"
                    ],
                    "batch_size": 50,
                    "max_comentarios_por_ejecucion": 200,
                    "ventana_procesamiento_horas": 24
                }
            }
            
            result = supabase.table('jobs_config').upsert(job_data).execute()
            print("✅ Job insertado manualmente")
            print(f"📊 Datos insertados: {result.data}")
            
        except Exception as e2:
            print(f"❌ Error en inserción manual: {e2}")

if __name__ == "__main__":
    aplicar_migracion()