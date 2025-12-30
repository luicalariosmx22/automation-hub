"""
Job para publicar posts de Facebook a Google Business Profile.
"""
import logging
from datetime import datetime
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import create_local_post
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "meta.to_gbp.daily"


def run(ctx=None):
    """
    Ejecuta el job de publicación de posts de Facebook a GBP.
    
    1. Obtiene token de acceso de Google
    2. Lee publicaciones pendientes de meta_publicaciones_webhook
    3. Para cada publicación:
       - Obtiene empresa_id desde facebook_paginas
       - Obtiene locaciones activas de esa empresa
       - Publica en cada locación de GBP
       - Registra en gbp_publicaciones
       - Marca como procesada
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Obtener header de autorización (valida OAuth internamente)
    logger.info("Obteniendo credenciales de Google OAuth")
    auth_header = get_bearer_header()
    
    # Crear cliente Supabase (valida variables internamente)
    supabase = create_client_from_env()
    
    # Obtener publicaciones pendientes CON MENSAJE que NO se hayan publicado en GBP
    logger.info("Obteniendo publicaciones pendientes para GBP (solo con mensaje)")
    response = supabase.table("meta_publicaciones_webhook").select("*").eq("publicada_gbp", False).not_.is_("mensaje", "null").execute()
    publicaciones = response.data
    
    if not publicaciones:
        logger.info("No hay publicaciones pendientes con mensaje para publicar en GBP")
        return
    
    logger.info(f"Publicaciones pendientes con mensaje para GBP: {len(publicaciones)}")
    
    # Estadísticas
    total_procesadas = 0
    total_publicaciones_gbp = 0
    errores = 0
    
    for pub in publicaciones:
        page_id = pub.get("page_id")
        post_id = pub.get("post_id")
        mensaje = pub.get("mensaje")
        imagen_url = pub.get("imagen_url")
        imagen_local = pub.get("imagen_local")
        
        if not page_id or not mensaje:
            logger.warning(f"Publicación incompleta (sin page_id o mensaje): {pub}")
            continue
        
        # Las imágenes están en servidor local, pero necesitamos que sean públicamente accesibles
        # Si imagen_local no es accesible, descargar imagen_url y subirla a Supabase Storage
        imagen_url_publica = None
        
        def descargar_y_subir_imagen_a_storage(url_imagen, post_id, page_id):
            """Descarga imagen y la sube a Supabase Storage para que sea públicamente accesible"""
            try:
                import requests
                from datetime import datetime
                
                if not url_imagen:
                    return None
                
                # Descargar imagen
                response = requests.get(url_imagen, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"No se pudo descargar imagen: HTTP {response.status_code}")
                    return None
                
                # Obtener extensión del content-type
                content_type = response.headers.get('content-type', 'image/jpeg')
                ext = 'jpg'
                if 'png' in content_type:
                    ext = 'png'
                elif 'gif' in content_type:
                    ext = 'gif'
                elif 'webp' in content_type:
                    ext = 'webp'
                
                # Nombre del archivo: posts/{page_id}/{post_id}_{timestamp}.{ext}
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_path = f"posts/{page_id}/{post_id}_{timestamp}.{ext}"
                
                # Subir a Supabase Storage
                result = supabase.storage.from_('meta-webhooks').upload(
                    file_path,
                    response.content,
                    {
                        'content-type': content_type,
                        'cache-control': '3600',
                        'upsert': 'true'
                    }
                )
                
                # Obtener URL pública
                public_url = supabase.storage.from_('meta-webhooks').get_public_url(file_path)
                logger.info(f"Imagen subida a Storage: {file_path}")
                return public_url
                
            except Exception as e:
                logger.error(f"Error subiendo imagen a Storage: {e}")
                return None
        
        if imagen_local:
            try:
                import requests
                response = requests.head(imagen_local, timeout=5)
                if response.status_code == 200:
                    imagen_url_publica = imagen_local
                    logger.info(f"Usando imagen_local accesible: {imagen_local}")
                else:
                    logger.warning(f"imagen_local no accesible (HTTP {response.status_code}), intentando subir a Storage")
                    # Si imagen_local no es accesible, usar imagen_url y subirla a Storage
                    if imagen_url:
                        imagen_url_publica = descargar_y_subir_imagen_a_storage(imagen_url, post_id, page_id)
            except Exception as e:
                logger.warning(f"Error verificando imagen_local: {e}")
                # Si imagen_local falla, usar imagen_url y subirla a Storage
                if imagen_url:
                    imagen_url_publica = descargar_y_subir_imagen_a_storage(imagen_url, post_id, page_id)
        elif imagen_url:
            # Solo tenemos imagen_url, subirla a Storage
            imagen_url_publica = descargar_y_subir_imagen_a_storage(imagen_url, post_id, page_id)
        
        if not imagen_url_publica:
            logger.info("Publicando solo texto (sin imagen accesible)")
        
        try:
            # Obtener empresa_id y verificar si debe publicarse en GBP
            logger.info(f"Buscando empresa para page_id: {page_id}")
            pagina_response = supabase.table("facebook_paginas").select("empresa_id, publicar_en_gbp").eq("page_id", page_id).execute()
            
            if not pagina_response.data:
                logger.warning(f"No se encontró empresa_id para page_id: {page_id}")
                # Marcar como publicada_gbp=True para no volver a intentar
                supabase.table("meta_publicaciones_webhook").update({"publicada_gbp": True}).eq("id", pub["id"]).execute()
                continue
            
            pagina_data = pagina_response.data[0]
            empresa_id = pagina_data.get("empresa_id")
            publicar_en_gbp = pagina_data.get("publicar_en_gbp", False)
            
            # Verificar si esta página debe publicarse en GBP
            if not publicar_en_gbp:
                logger.info(f"Página {page_id} tiene publicar_en_gbp=False, omitiendo")
                # Marcar como publicada_gbp=True para no volver a procesar
                supabase.table("meta_publicaciones_webhook").update({"publicada_gbp": True}).eq("id", pub["id"]).execute()
                continue
            
            logger.info(f"Empresa encontrada: {empresa_id} (publicar_en_gbp=True)")
            
            # Obtener locaciones activas de esa empresa
            locations_response = supabase.table("gbp_locations").select("location_name, nombre_nora").eq("empresa_id", empresa_id).eq("activa", True).execute()
            
            if not locations_response.data:
                logger.warning(f"No se encontraron locaciones activas para empresa_id: {empresa_id}")
                # Marcar como publicada_gbp=True para no volver a intentar
                supabase.table("meta_publicaciones_webhook").update({"publicada_gbp": True}).eq("id", pub["id"]).execute()
                continue
            
            locaciones = locations_response.data
            logger.info(f"Locaciones activas encontradas: {len(locaciones)}")
            
            # Publicar en cada locación
            for loc in locaciones:
                location_name = loc.get("location_name")
                nombre_nora = loc.get("nombre_nora", "Sistema")
                
                if not location_name:
                    logger.warning(f"Locación sin location_name: {loc}")
                    continue
                
                try:
                    logger.info(f"Publicando en {location_name}")
                    
                    # Crear post en GBP con imagen desde Supabase Storage público
                    gbp_post = create_local_post(
                        location_name=location_name,
                        auth_header=auth_header,
                        summary=mensaje,
                        media_url=imagen_url_publica
                    )
                    
                    # Registrar en gbp_publicaciones
                    gbp_post_name = gbp_post.get("name", "N/A")
                    supabase.table("gbp_publicaciones").insert({
                        "location_name": location_name,
                        "nombre_nora": nombre_nora,
                        "tipo": "FROM_FACEBOOK",
                        "estado": "publicada",
                        "gbp_post_name": gbp_post_name,
                        "contenido": mensaje,
                        "imagen_url": imagen_url_publica,
                        "published_at": datetime.utcnow().isoformat()
                    }).execute()
                    
                    total_publicaciones_gbp += 1
                    logger.info(f"Post publicado exitosamente en {location_name}")
                
                except Exception as e:
                    logger.error(f"Error publicando en {location_name}: {e}", exc_info=True)
                    
                    # Registrar error en gbp_publicaciones
                    supabase.table("gbp_publicaciones").insert({
                        "location_name": location_name,
                        "nombre_nora": nombre_nora,
                        "tipo": "FROM_FACEBOOK",
                        "estado": "error",
                        "contenido": mensaje,
                        "imagen_url": imagen_url_publica or imagen_local,
                        "error_mensaje": str(e)[:500],
                        "created_at": datetime.utcnow().isoformat()
                    }).execute()
                    
                    errores += 1
                    continue
            
            # Marcar como publicada en GBP
            supabase.table("meta_publicaciones_webhook").update({"publicada_gbp": True}).eq("id", pub["id"]).execute()
            total_procesadas += 1
            logger.info(f"Publicación {post_id} publicada en GBP completamente")
        
        except Exception as e:
            logger.error(f"Error procesando publicación {post_id}: {e}", exc_info=True)
            errores += 1
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Publicaciones procesadas: {total_procesadas}, Posts en GBP: {total_publicaciones_gbp}, Errores: {errores}")
    
    # Crear alerta de job completado y notificar por Telegram
    try:
        mensaje_resumen = (
            f"✅ Posts Facebook → GBP sincronizados\n\n"
            f"📊 Publicaciones procesadas: {total_procesadas}\n"
            f"📍 Posts creados en GBP: {total_publicaciones_gbp}\n"
            f"❌ Errores: {errores}"
        )
        
        crear_alerta(
            supabase=supabase,
            nombre=f"Posts Facebook → GBP",
            tipo="job_completado",
            nombre_nora="sistema",
            descripcion=mensaje_resumen,
            datos={"job_name": JOB_NAME}
        )
        
        # Enviar notificación usando el bot principal
        telegram = TelegramNotifier(bot_nombre="Bot Principal")
        telegram.enviar_alerta(
            nombre="Posts Facebook → GBP",
            descripcion=mensaje_resumen,
            prioridad="baja"
        )
    except Exception as e:
        logger.error(f"Error enviando notificación: {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run()
