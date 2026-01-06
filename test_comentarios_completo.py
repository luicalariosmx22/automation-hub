#!/usr/bin/env python3
"""
Script para simular comentarios y probar las reglas de automatización
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import time

# Cargar variables de entorno
load_dotenv()

# Configurar PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def insertar_comentario_test(supabase, comentario_data):
    """Inserta un comentario de prueba"""
    try:
        result = supabase.table('meta_comentarios_webhook').insert(comentario_data).execute()
        print(f"✅ Comentario insertado: {comentario_data['mensaje'][:50]}...")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error insertando comentario: {e}")
        return None

def crear_comentarios_test():
    """Crea comentarios de prueba para diferentes escenarios"""
    from automation_hub.db.supabase_client import create_client_from_env
    
    supabase = create_client_from_env()
    
    # Limpiar comentarios de prueba previos
    try:
        supabase.table('meta_comentarios_webhook').delete().like('comment_id', 'test_%').execute()
        print("🧹 Comentarios de prueba previos eliminados")
    except:
        pass
    
    comentarios_test = [
        {
            "nombre_nora": "Sistema",
            "page_id": "123456789",
            "post_id": "post_test_1",
            "comment_id": f"test_info_{int(time.time())}",
            "mensaje": "Hola, me gustaría saber el precio de este producto. ¿Podrían enviarme información?",
            "from_id": "user_001",
            "from_name": "Ana García", 
            "created_time": int(time.time()),
            "procesada": False
        },
        {
            "nombre_nora": "Sistema",
            "page_id": "123456789",
            "post_id": "post_test_2",
            "comment_id": f"test_negativo_{int(time.time())}",
            "mensaje": "Pésimo servicio, no funciona nada. Muy malo todo.",
            "from_id": "user_002", 
            "from_name": "Carlos López",
            "created_time": int(time.time()),
            "procesada": False
        },
        {
            "nombre_nora": "Sistema",
            "page_id": "123456789",
            "post_id": "post_test_3", 
            "comment_id": f"test_compra_{int(time.time())}",
            "mensaje": "Quiero comprar este producto. ¿Me interesa mucho, cómo puedo adquirirlo?",
            "from_id": "user_003",
            "from_name": "María Rodríguez",
            "created_time": int(time.time()),
            "procesada": False
        },
        {
            "nombre_nora": "Sistema", 
            "page_id": "123456789",
            "post_id": "post_test_4",
            "comment_id": f"test_saludo_{int(time.time())}",
            "mensaje": "¡Hola! Buenos días, muy interesante su página.",
            "from_id": "user_004",
            "from_name": "Juan Pérez",
            "created_time": int(time.time()),
            "procesada": False
        },
        {
            "nombre_nora": "Sistema",
            "page_id": "123456789", 
            "post_id": "post_test_5",
            "comment_id": f"test_normal_{int(time.time())}",
            "mensaje": "Me gusta mucho este producto, se ve muy bien.",
            "from_id": "user_005",
            "from_name": "Laura Martínez",
            "created_time": int(time.time()),
            "procesada": False
        }
    ]
    
    print("📝 Insertando comentarios de prueba...")
    comentarios_insertados = []
    
    for comentario in comentarios_test:
        resultado = insertar_comentario_test(supabase, comentario)
        if resultado:
            comentarios_insertados.append(resultado)
        time.sleep(0.5)  # Evitar rate limiting
    
    print(f"✅ {len(comentarios_insertados)} comentarios de prueba creados")
    return comentarios_insertados

def ejecutar_job_y_ver_resultados():
    """Ejecuta el job y muestra los resultados"""
    print("\n🤖 Ejecutando job de automatización...")
    
    from automation_hub.jobs.meta_comentarios_automation import run
    run()
    
    # Verificar resultados
    print("\n📊 Verificando resultados...")
    from automation_hub.db.supabase_client import create_client_from_env
    
    supabase = create_client_from_env()
    
    # Ver comentarios procesados
    procesados = supabase.table('meta_comentarios_webhook').select(
        'comment_id, mensaje, procesada, procesada_en'
    ).like('comment_id', 'test_%').eq('procesada', True).execute()
    
    if procesados.data:
        print(f"\n✅ Comentarios procesados: {len(procesados.data)}")
        for comentario in procesados.data:
            print(f"   - {comentario['comment_id']}: '{comentario['mensaje'][:40]}...'")
    else:
        print("\n❌ No se procesaron comentarios")
    
    # Ver alertas generadas
    alertas = supabase.table('alertas').select(
        'nombre, descripcion, prioridad, creada_en'
    ).eq('evento_origen', 'meta.comentarios.automation').order('creada_en', desc=True).limit(10).execute()
    
    if alertas.data:
        print(f"\n🚨 Alertas generadas: {len(alertas.data)}")
        for alerta in alertas.data:
            print(f"   - {alerta['nombre']}: {alerta['descripcion']}")
    else:
        print("\n📝 No se generaron alertas")

if __name__ == "__main__":
    print("🧪 Iniciando prueba de automatización de comentarios...")
    
    # Crear comentarios de prueba
    comentarios = crear_comentarios_test()
    
    if comentarios:
        print(f"\n⏳ Esperando 2 segundos...")
        time.sleep(2)
        
        # Ejecutar job
        ejecutar_job_y_ver_resultados()
    else:
        print("❌ No se pudieron crear comentarios de prueba")
    
    print("\n✅ Prueba completada")