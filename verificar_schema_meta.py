"""
Verifica el schema real de meta_publicaciones_webhook en Supabase
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

# Obtener una publicación para ver las columnas
result = supabase.table('meta_publicaciones_webhook').select('*').limit(1).execute()

if result.data:
    print("\n" + "="*80)
    print("📊 COLUMNAS EN meta_publicaciones_webhook (Supabase):")
    print("="*80 + "\n")
    
    columnas = sorted(result.data[0].keys())
    
    # Agrupar por categoría
    campos_basicos = []
    campos_imagen = []
    campos_video = []
    campos_sistema = []
    
    for col in columnas:
        if 'video' in col:
            campos_video.append(col)
        elif 'imagen' in col or 'thumbnail' in col:
            campos_imagen.append(col)
        elif col in ['id', 'post_id', 'page_id', 'mensaje', 'tipo_item', 'created_time', 'webhook_data', 'nombre_nora']:
            campos_basicos.append(col)
        else:
            campos_sistema.append(col)
    
    print("📋 Campos Básicos:")
    for col in campos_basicos:
        print(f"  ✓ {col}")
    
    print("\n🖼️  Campos de Imagen:")
    for col in campos_imagen:
        print(f"  ✓ {col}")
    
    print("\n🎥 Campos de Video:")
    if campos_video:
        for col in campos_video:
            print(f"  ✓ {col}")
    else:
        print("  ❌ NO HAY CAMPOS DE VIDEO - Necesita migración")
    
    print("\n⚙️  Campos de Sistema:")
    for col in campos_sistema:
        print(f"  ✓ {col}")
    
    print("\n" + "="*80)
    print(f"Total de columnas: {len(columnas)}")
    print("="*80 + "\n")
    
    # Verificar campos necesarios para el job
    campos_requeridos = ['imagen_url', 'imagen_local', 'video_local', 'tipo_item', 'mensaje']
    campos_faltantes = [c for c in campos_requeridos if c not in columnas]
    
    if campos_faltantes:
        print("⚠️  FALTAN CAMPOS REQUERIDOS:")
        for campo in campos_faltantes:
            print(f"  ❌ {campo}")
        print(f"\n👉 Ejecutar migración: migrations/add_video_fields_meta_publicaciones.sql")
    else:
        print("✅ TODOS LOS CAMPOS REQUERIDOS EXISTEN")
        print("   El job puede ejecutarse sin problemas")
    
    print()
else:
    print("⚠️  No hay publicaciones en la tabla (tabla vacía)")
    print("   No se pueden verificar las columnas")
