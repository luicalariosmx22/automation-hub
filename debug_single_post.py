#!/usr/bin/env python3
"""
Script para debug - procesar solo 1 publicación para ver el error 400
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import create_local_post

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_single_publication():
    """Debug de una sola publicación"""
    logger.info("🔍 DEBUG: Procesando 1 publicación para diagnóstico")
    
    supabase = create_client_from_env()
    auth_header = get_bearer_header()
    
    # Obtener UNA publicación pendiente CON MENSAJE
    response = supabase.table("meta_publicaciones_webhook")\
        .select("*")\
        .eq("publicada_gbp", False)\
        .gte("creada_en", "2025-12-01")\
        .not_.is_("mensaje", "null")\
        .neq("mensaje", "")\
        .order("creada_en", desc=True)\
        .limit(1)\
        .execute()
    
    if not response.data:
        logger.info("No hay publicaciones pendientes")
        return
    
    pub = response.data[0]
    page_id = pub.get("page_id")
    post_id = pub.get("post_id")
    mensaje = pub.get("mensaje", "")
    imagen_local = pub.get("imagen_local")
    imagen_url = pub.get("imagen_url")
    
    logger.info(f"📝 Procesando: {post_id}")
    logger.info(f"📄 Page ID: {page_id}")
    logger.info(f"📝 Mensaje: {mensaje[:100] if mensaje else 'None'}...")
    logger.info(f"🖼️ Imagen local: {imagen_local}")
    logger.info(f"🖼️ Imagen URL: {imagen_url}")
    
    if not mensaje:
        logger.warning("❌ Mensaje es None o vacío, saltando...")
        return
    
    # Obtener empresa_id
    pagina_response = supabase.table("facebook_paginas")\
        .select("empresa_id, publicar_en_gbp")\
        .eq("page_id", page_id)\
        .execute()
    
    if not pagina_response.data:
        logger.warning(f"❌ No se encontró empresa para page_id: {page_id}")
        return
    
    empresa_id = pagina_response.data[0].get("empresa_id")
    publicar_en_gbp = pagina_response.data[0].get("publicar_en_gbp", False)
    
    logger.info(f"🏢 Empresa: {empresa_id}")
    logger.info(f"📋 Publicar en GBP: {publicar_en_gbp}")
    
    if not publicar_en_gbp:
        logger.info("❌ Empresa no tiene publicar_en_gbp activo")
        return
    
    # Obtener ubicaciones activas
    ubicaciones_response = supabase.table("gbp_locations")\
        .select("*")\
        .eq("empresa_id", empresa_id)\
        .eq("activa", True)\
        .execute()
    
    if not ubicaciones_response.data:
        logger.warning(f"❌ No hay ubicaciones activas para empresa: {empresa_id}")
        return
    
    ubicacion = ubicaciones_response.data[0]  # Usar la primera ubicación
    location_name = ubicacion.get("location_name")
    
    logger.info(f"📍 Ubicación: {location_name}")
    
    # Solo texto por ahora para debug
    imagen_url_publica = None
    
    logger.info("🚀 Intentando publicar en GBP...")
    
    try:
        gbp_post = create_local_post(
            location_name=location_name,
            auth_header=auth_header,
            summary=mensaje,
            media_url=imagen_url_publica
        )
        
        logger.info(f"✅ ÉXITO: {gbp_post}")
        
        # Marcar como publicada
        supabase.table("meta_publicaciones_webhook")\
            .update({"publicada_gbp": True})\
            .eq("id", pub.get("id"))\
            .execute()
        
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        logger.error(f"❌ Tipo de error: {type(e)}")

if __name__ == "__main__":
    debug_single_publication()