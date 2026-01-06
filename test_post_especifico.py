#!/usr/bin/env python3
"""
Script para probar un post específico que tiene ubicación GBP activa
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import create_local_post

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_post_especifico():
    """
    Prueba un post específico que sabemos tiene ubicación activa
    """
    post_id = "244796979033974_1294237509401540"
    
    try:
        # Crear cliente Supabase
        supabase = create_client_from_env()
        logger.info(f"🧪 PROBANDO POST ESPECÍFICO: {post_id}")
        
        # Obtener datos del post
        post_response = supabase.table("meta_publicaciones_webhook").select("*").eq("post_id", post_id).execute()
        
        if not post_response.data:
            logger.error(f"❌ Post {post_id} no encontrado en base de datos")
            return
        
        pub = post_response.data[0]
        logger.info(f"✅ Post encontrado: {pub.get('mensaje', 'Sin mensaje')[:50]}...")
        
        page_id = pub.get("page_id")
        mensaje = pub.get("mensaje", "")
        imagen_local = pub.get("imagen_local")
        imagen_url = pub.get("imagen_url")
        
        # Obtener empresa_id
        pagina_response = supabase.table("facebook_paginas").select("empresa_id, publicar_en_gbp").eq("page_id", page_id).execute()
        
        if not pagina_response.data:
            logger.error(f"❌ No se encontró empresa para page_id: {page_id}")
            return
            
        empresa_data = pagina_response.data[0]
        empresa_id = empresa_data.get("empresa_id")
        publicar_en_gbp = empresa_data.get("publicar_en_gbp", False)
        
        logger.info(f"📊 Empresa: {empresa_id}")
        logger.info(f"📊 Publicar en GBP: {publicar_en_gbp}")
        
        if not publicar_en_gbp:
            logger.warning("⚠️ Esta empresa tiene publicar_en_gbp = False")
            
        # Obtener ubicaciones activas
        ubicaciones_response = supabase.table("gbp_locations").select("*").eq("empresa_id", empresa_id).eq("activa", True).execute()
        
        if not ubicaciones_response.data:
            logger.error(f"❌ No hay ubicaciones activas para empresa {empresa_id}")
            
            # Mostrar ubicaciones inactivas
            inactivas = supabase.table("gbp_locations").select("*").eq("empresa_id", empresa_id).eq("activa", False).execute()
            if inactivas.data:
                logger.info(f"📋 Ubicaciones inactivas encontradas: {len(inactivas.data)}")
                for ub in inactivas.data[:3]:
                    logger.info(f"   🔸 {ub.get('location_name', 'Sin nombre')}")
            return
            
        ubicaciones = ubicaciones_response.data
        logger.info(f"✅ Ubicaciones activas encontradas: {len(ubicaciones)}")
        
        # Procesar imágenes
        imagen_url_publica = None
        
        if imagen_local and isinstance(imagen_local, str):
            if 'soynoraai.com' in imagen_local:
                logger.warning(f"⚠️ Ignorando imagen_local de soynoraai.com: {imagen_local}")
            elif 'fbcdn.net' in imagen_local or 'facebook.com' in imagen_local:
                logger.warning(f"⚠️ Ignorando imagen_local de Facebook: {imagen_local}")
            elif 'supabase.co/storage/v1/object/public' in imagen_local:
                imagen_url_publica = imagen_local
                logger.info(f"✅ Usando imagen_local de Supabase: {imagen_local}")
            else:
                imagen_url_publica = imagen_local
                logger.info(f"✅ Usando imagen_local externa: {imagen_local}")
        elif imagen_url and isinstance(imagen_url, str):
            if 'fbcdn.net' in imagen_url or 'facebook.com' in imagen_url:
                logger.warning(f"⚠️ Ignorando imagen_url de Facebook: {imagen_url}")
            elif 'soynoraai.com' in imagen_url:
                logger.warning(f"⚠️ Ignorando imagen_url de soynoraai.com: {imagen_url}")
            else:
                imagen_url_publica = imagen_url
                logger.info(f"✅ Usando imagen_url externa: {imagen_url}")
        
        if not imagen_url_publica:
            logger.info("📝 Publicando solo texto (sin imagen)")
        
        # Probar con la primera ubicación activa
        ubicacion = ubicaciones[0]
        location_name = ubicacion.get("location_name")
        logger.info(f"🎯 Probando con ubicación: {location_name}")
        
        # Obtener token de autorización
        auth_header = get_bearer_header()
        logger.info("🔑 Token de autorización obtenido")
        
        # Crear post en GBP
        gbp_post = create_local_post(
            location_name=location_name,
            auth_header=auth_header,
            summary=mensaje,
            media_url=imagen_url_publica
        )
        
        logger.info(f"✅ POST CREADO EXITOSAMENTE EN GBP!")
        logger.info(f"📄 Respuesta: {gbp_post}")
        
        # Marcar como publicada
        supabase.table("meta_publicaciones_webhook").update({"publicada_gbp": True}).eq("id", pub["id"]).execute()
        logger.info("✅ Marcado como publicada_gbp = True")
        
    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}", exc_info=True)

if __name__ == "__main__":
    test_post_especifico()