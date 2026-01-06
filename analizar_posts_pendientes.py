#!/usr/bin/env python3
"""
Analizar posts pendientes para ver cuántos videos vs imágenes tenemos
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
from automation_hub.db.supabase_client import create_client_from_env

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analizar_posts_pendientes():
    """Analizar cuántos posts pendientes tenemos y de qué tipo"""
    
    supabase = create_client_from_env()
    
    # Buscar publicaciones pendientes recientes  
    response = supabase.table("meta_publicaciones_webhook")\
        .select("*")\
        .eq("publicada_gbp", False)\
        .limit(5)\
        .execute()
    
    # Ver campos disponibles
    if response.data:
        print("📋 CAMPOS DISPONIBLES:")
        for campo in response.data[0].keys():
            print(f"   - {campo}")
        print()
    
    # Buscar publicaciones pendientes recientes
    response = supabase.table("meta_publicaciones_webhook")\
        .select("post_id, mensaje, imagen_url, imagen_local, video_local, page_id")\
        .eq("publicada_gbp", False)\
        .order("id", desc=False)\
        .execute()
    
    if not response.data:
        print("❌ No hay publicaciones pendientes")
        return
    
    total = len(response.data)
    videos = 0
    imagenes = 0
    solo_texto = 0
    
    posts_video = []
    posts_imagen = []
    
    print(f"\n📊 ANÁLISIS DE {total} POSTS PENDIENTES\n")
    
    # ANÁLISIS DETALLADO DE VIDEO_LOCAL
    posts_con_video_local = 0
    posts_con_imagen_local = 0
    posts_con_imagen_url = 0
    
    for pub in response.data:
        post_id = pub.get("post_id")
        video_local = pub.get("video_local")
        imagen_local = pub.get("imagen_local") 
        imagen_url = pub.get("imagen_url")
        created_at = pub.get("id", "N/A")  # Usar ID como referencia
        mensaje = (pub.get("mensaje") or "")[:50]
        
        # CONTADORES ESPECÍFICOS
        if video_local:
            posts_con_video_local += 1
        if imagen_local:
            posts_con_imagen_local += 1  
        if imagen_url:
            posts_con_imagen_url += 1
        
        # Determinar tipo (PRIORIZAR VIDEO_LOCAL)
        if video_local and video_local.strip():  # Video existe y no está vacío
            videos += 1
            posts_video.append({
                "post_id": post_id,
                "created_at": created_at,
                "mensaje": mensaje,
                "video_url": video_local[:80] + "..." if len(video_local) > 80 else video_local
            })
        elif imagen_local or imagen_url:
            imagenes += 1
            posts_imagen.append({
                "post_id": post_id, 
                "created_at": created_at,
                "mensaje": mensaje
            })
        else:
            solo_texto += 1
    
    print(f"📊 ESTADÍSTICAS DETALLADAS:")
    print(f"   🗂️  Posts con video_local: {posts_con_video_local}")
    print(f"   🗂️  Posts con imagen_local: {posts_con_imagen_local}")
    print(f"   🗂️  Posts con imagen_url: {posts_con_imagen_url}")
    print()
    print(f"📊 CLASIFICACIÓN FINAL:")
    print(f"   🎥 Videos (video_local válidos): {videos}")
    print(f"   🖼️  Imágenes: {imagenes}")
    print(f"   📝 Solo texto: {solo_texto}")
    print(f"   📊 Total: {total}")
    print()
    
    # Mostrar algunos videos de ejemplo
    if posts_video:
        print("🎥 PRIMEROS 5 VIDEOS:")
        for i, post in enumerate(posts_video[:5]):
            fecha = post["created_at"][:10] if post["created_at"] else "N/A"
            print(f"   {i+1}. {post['post_id']} • {fecha} • {post['mensaje']}...")
        
        if len(posts_video) > 5:
            print(f"   ... y {len(posts_video) - 5} videos más")
        print()
    
    # Mostrar algunas imágenes de ejemplo  
    if posts_imagen:
        print("🖼️  PRIMERAS 5 IMÁGENES:")
        for i, post in enumerate(posts_imagen[:5]):
            fecha = post["created_at"][:10] if post["created_at"] else "N/A" 
            print(f"   {i+1}. {post['post_id']} • {fecha} • {post['mensaje']}...")
        print()
    
    # Recomendación de processing
    if videos > 10:
        print("⚠️  RECOMENDACIÓN:")
        print(f"   Tienes {videos} videos pendientes.")
        print(f"   Para evitar spam en GBP, te sugiero:")
        print(f"   • Procesar máximo 5-10 videos por vez")
        print(f"   • Usar delay de 1-2 minutos entre videos")
        print(f"   • O limitar a solo imágenes por ahora")
    
    return {
        "total": total,
        "videos": videos, 
        "imagenes": imagenes,
        "solo_texto": solo_texto,
        "posts_video": posts_video,
        "posts_imagen": posts_imagen
    }

if __name__ == "__main__":
    analizar_posts_pendientes()