#!/usr/bin/env python3
"""
Buscar videos en TODA la tabla, no solo pendientes
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def buscar_todos_videos():
    """Buscar todos los videos en la tabla"""
    
    supabase = create_client_from_env()
    
    # Buscar TODOS los posts con video_local (no importa si están publicados)
    print("🔍 Buscando TODOS los videos en la tabla...\n")
    
    # Buscar posts que tengan algo en video_local
    response = supabase.table("meta_publicaciones_webhook")\
        .select("post_id, video_local, publicada_gbp, creada_en")\
        .order("id", desc=True)\
        .execute()
    
    # Filtrar manualmente los que tienen video_local
    posts_con_video = []
    for pub in response.data:
        video_local = pub.get("video_local")
        if video_local and video_local.strip():  # No está vacío ni es None
            posts_con_video.append(pub)
    
    if not posts_con_video:
        print("❌ No se encontraron videos en toda la tabla")
        return
    
    # Tomar solo los primeros 20 para mostrar
    posts_con_video = posts_con_video[:20]
    
    print(f"📊 VIDEOS ENCONTRADOS: {len(posts_con_video)} (últimos 20)\n")
    
    pendientes = 0
    publicados = 0
    
    for i, pub in enumerate(posts_con_video):
        post_id = pub.get("post_id")
        video_local = pub.get("video_local")
        publicada_gbp = pub.get("publicada_gbp", False)
        fecha = pub.get("creada_en", "N/A")[:10] if pub.get("creada_en") else "N/A"
        
        estado = "✅ PUBLICADO" if publicada_gbp else "⏳ PENDIENTE"
        
        if publicada_gbp:
            publicados += 1
        else:
            pendientes += 1
        
        print(f"{i+1:2d}. {estado} • {fecha} • {post_id}")
        print(f"    📎 {video_local[:80]}...")
        print()
    
    print(f"📊 RESUMEN:")
    print(f"   ⏳ Videos pendientes: {pendientes}")
    print(f"   ✅ Videos ya publicados: {publicados}")
    print(f"   📊 Total videos: {len(posts_con_video)}")
    
    # Contar todos los pendientes
    todos_pendientes = []
    for pub in response.data:
        video_local = pub.get("video_local")
        publicada_gbp = pub.get("publicada_gbp", False)
        if video_local and video_local.strip() and not publicada_gbp:
            todos_pendientes.append(pub)
    
    print(f"\n🎯 Videos realmente PENDIENTES en toda la BD: {len(todos_pendientes)}")

if __name__ == "__main__":
    buscar_todos_videos()