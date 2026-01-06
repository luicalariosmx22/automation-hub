#!/usr/bin/env python3
"""
Script para probar post específico: 111573020717136_1419829143487490
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
from datetime import datetime
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import create_local_post
from automation_hub.integrations.telegram.notifier import TelegramNotifier

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def probar_post_especifico():
    """Probar post específico 111573020717136_1419829143487490"""
    post_id = "111573020717136_1419829143487490"
    
    logger.info(f"🔍 Analizando post específico: {post_id}")
    
    supabase = create_client_from_env()
    auth_header = get_bearer_header()
    
    # Buscar el post específico
    response = supabase.table("meta_publicaciones_webhook")\
        .select("*")\
        .eq("post_id", post_id)\
        .execute()
    
    if not response.data:
        print(f"❌ No se encontró el post {post_id}")
        return
    
    pub = response.data[0]
    page_id = pub.get("page_id")
    mensaje = pub.get("mensaje", "")
    imagen_local = pub.get("imagen_local")
    imagen_url = pub.get("imagen_url")
    video_local = pub.get("video_local")
    
    print(f"📝 POST ENCONTRADO:")
    print(f"   📄 Page ID: {page_id}")
    print(f"   📝 Mensaje: {mensaje[:100]}..." if mensaje else "   📝 Sin mensaje")
    print(f"   🖼️ Imagen local: {imagen_local}")
    print(f"   🖼️ Imagen URL: {imagen_url}")
    print(f"   🎥 Video local: {video_local}")
    print()
    
    # Determinar tipo de contenido - PRIORIZAR video_local
    contenido_tipo = "texto"
    media_url = None
    
    if video_local:
        contenido_tipo = "video_supabase"
        media_url = video_local
        print(f"🎯 USANDO VIDEO DE SUPABASE: {video_local}")
    elif imagen_local:
        if any(ext in imagen_local.lower() for ext in ['.mp4', '.mov', '.avi', 'video']):
            contenido_tipo = "video"
            media_url = imagen_local
        elif any(ext in imagen_local.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            contenido_tipo = "imagen"
            media_url = imagen_local
        else:
            contenido_tipo = "media_desconocido"
            media_url = imagen_local
    elif imagen_url:
        if any(ext in imagen_url.lower() for ext in ['.mp4', '.mov', '.avi', 'video']):
            contenido_tipo = "video"
            media_url = imagen_url
        elif any(ext in imagen_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            contenido_tipo = "imagen"
            media_url = imagen_url
        else:
            contenido_tipo = "media_desconocido"
            media_url = imagen_url
    
    print(f"🎯 TIPO DE CONTENIDO DETECTADO: {contenido_tipo.upper()}")
    if media_url:
        print(f"📎 URL: {media_url[:80]}...")
    print()
    
    # Obtener empresa y ubicaciones
    pagina_response = supabase.table("facebook_paginas")\
        .select("empresa_id, publicar_en_gbp")\
        .eq("page_id", page_id)\
        .execute()
    
    if not pagina_response.data:
        print(f"❌ No se encontró empresa para page_id: {page_id}")
        return
    
    empresa_id = pagina_response.data[0].get("empresa_id")
    publicar_en_gbp = pagina_response.data[0].get("publicar_en_gbp", False)
    
    print(f"🏢 Empresa: {empresa_id}")
    print(f"📋 Publicar en GBP: {publicar_en_gbp}")
    
    if not publicar_en_gbp:
        print("❌ Empresa no tiene publicar_en_gbp activo")
        return
    
    # Obtener ubicaciones
    ubicaciones_response = supabase.table("gbp_locations")\
        .select("*")\
        .eq("empresa_id", empresa_id)\
        .eq("activa", True)\
        .execute()
    
    if not ubicaciones_response.data:
        print(f"❌ No hay ubicaciones activas para empresa: {empresa_id}")
        return
    
    ubicacion = ubicaciones_response.data[0]
    location_name = ubicacion.get("location_name")
    nombre_nora = ubicacion.get("nombre_nora", "Sin nombre")
    
    print(f"📍 Ubicación: {nombre_nora}")
    print(f"🆔 Location ID: {location_name}")
    print()
    
    if not mensaje:
        print("❌ Post sin mensaje, saltando...")
        return
    
    # INTENTAR PUBLICAR EN GBP
    print(f"🚀 INTENTANDO PUBLICAR EN GBP ({contenido_tipo})...")
    
    try:
        gbp_post = create_local_post(
            location_name=location_name,
            auth_header=auth_header,
            summary=mensaje,
            video_local=video_local,
            imagen_local=imagen_local,
            imagen_url=imagen_url
        )
        
        print(f"✅ ÉXITO! Post publicado en GBP:")
        print(f"   🆔 GBP Post: {gbp_post.get('name', 'N/A') if isinstance(gbp_post, dict) else 'N/A'}")
        print(f"   📍 En: {nombre_nora}")
        print()
        
        # Registrar en BD
        supabase.table("gbp_publicaciones").insert({
            "location_name": location_name,
            "nombre_nora": nombre_nora,
            "tipo": "FROM_FACEBOOK",
            "estado": "publicada",
            "gbp_post_name": gbp_post.get("name", "N/A") if isinstance(gbp_post, dict) else "N/A",
            "contenido": mensaje,
            "imagen_url": media_url,
            "published_at": datetime.utcnow().isoformat()
        }).execute()
        
        # Marcar como publicada
        supabase.table("meta_publicaciones_webhook")\
            .update({"publicada_gbp": True})\
            .eq("id", pub.get("id"))\
            .execute()
        
        # Enviar notificación
        try:
            telegram = TelegramNotifier(bot_nombre="bot de notificaciones")
            mensaje_corto = mensaje[:50] + "..." if len(mensaje) > 50 else mensaje
            icon = "🎥" if contenido_tipo == "video" else "🖼️" if contenido_tipo == "imagen" else "📝"
            
            mensaje_notif = f"""✅ **PUBLICACIÓN EXITOSA EN GBP** (PRUEBA)

📍 **{nombre_nora}**
📝 "{mensaje_corto}"
{icon} Tipo: {contenido_tipo}
⏰ {datetime.now().strftime('%H:%M')} • `{post_id}`"""
            
            if media_url and contenido_tipo == "imagen":
                telegram.enviar_imagen(media_url, mensaje_notif)
            else:
                telegram.enviar_mensaje(mensaje_notif)
            print("📱 Notificación enviada")
        except Exception as e:
            print(f"⚠️ Error en notificación: {e}")
        
    except Exception as e:
        print(f"❌ ERROR publicando en GBP: {e}")
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    probar_post_especifico()