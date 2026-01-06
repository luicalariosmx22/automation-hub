#!/usr/bin/env python3
"""
Script para probar el filtrado mejorado - solo imágenes válidas
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

def probar_filtrado_imagenes():
    """Probar qué publicaciones tienen imágenes válidas vs videos"""
    logger.info("🔍 Probando filtrado de imágenes vs videos")
    
    supabase = create_client_from_env()
    
    # Obtener algunas publicaciones pendientes para analizar
    response = supabase.table("meta_publicaciones_webhook")\
        .select("post_id, page_id, imagen_url, imagen_local")\
        .eq("publicada_gbp", False)\
        .gte("creada_en", "2025-12-01")\
        .not_.is_("mensaje", "null")\
        .neq("mensaje", "")\
        .order("creada_en", desc=True)\
        .limit(10)\
        .execute()
    
    if not response.data:
        logger.info("No hay publicaciones pendientes")
        return
    
    # Importar la función de filtrado
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from automation_hub.jobs.meta_to_gbp_daily import es_url_valida_para_gbp
    
    validas = 0
    rechazadas = 0
    
    for pub in response.data:
        post_id = pub.get("post_id", "")
        imagen_local = pub.get("imagen_local")
        imagen_url = pub.get("imagen_url")
        
        print(f"\n📝 Post: {post_id}")
        
        imagen_valida = False
        
        if imagen_local:
            if es_url_valida_para_gbp(imagen_local):
                print(f"✅ Imagen_local VÁLIDA: {imagen_local[:80]}...")
                imagen_valida = True
            else:
                print(f"❌ Imagen_local RECHAZADA: {imagen_local[:80]}...")
        
        if imagen_url and not imagen_valida:
            if es_url_valida_para_gbp(imagen_url):
                print(f"✅ Imagen_url VÁLIDA: {imagen_url[:80]}...")
                imagen_valida = True
            else:
                print(f"❌ Imagen_url RECHAZADA: {imagen_url[:80]}...")
        
        if not imagen_local and not imagen_url:
            print(f"⚫ Sin imágenes")
        
        if imagen_valida:
            print(f"🎉 POST SE PUBLICARÍA")
            validas += 1
        else:
            print(f"⏭️  POST SE SALTARÍA")
            rechazadas += 1
    
    print(f"\n📊 RESUMEN:")
    print(f"✅ Posts con imágenes válidas: {validas}")
    print(f"❌ Posts rechazados/saltados: {rechazadas}")
    print(f"📈 Porcentaje válido: {(validas/(validas+rechazadas)*100):.1f}%" if (validas+rechazadas) > 0 else "0%")

if __name__ == "__main__":
    probar_filtrado_imagenes()