"""
Job para publicar posts de Facebook a Google Business Profile.
"""
import logging
import time
from datetime import datetime
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import create_local_post
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "meta_to_gbp_daily"
MAX_VIDEOS_PER_RUN = 10  # Máximo videos por ejecución
VIDEO_DELAY_SECONDS = 120  # 2 minutos de delay entre videos


def es_url_valida_para_gbp(url: str) -> bool:
    """
    Verifica si una URL es válida para usar en Google Business Profile.
    SOLO ACEPTA URLs de Supabase Storage - rechaza Facebook, Instagram, etc.
    """
    if not url or not isinstance(url, str):
        return False
    
    # SOLO PERMITIR URLs DE SUPABASE STORAGE
    # Rechazar todo lo demás (Facebook, Instagram, URLs externas, etc.)
    if 'supabase.co/storage/v1/object/public' in url:
        logger.debug(f"✅ URL de Supabase Storage aceptada: {url[:60]}...")
        return True
    
    # Rechazar cualquier otra URL
    logger.debug(f"❌ URL rechazada (no es Supabase Storage): {url[:60]}...")
    return False


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
    # Solo procesamos publicaciones recientes: diciembre 2025 y enero 2026
    # Ordenadas de más nueva a más vieja
    logger.info("Obteniendo publicaciones pendientes para GBP (dic 2025 y ene 2026)")
    response = supabase.table("meta_publicaciones_webhook")\
        .select("*")\
        .eq("publicada_gbp", False)\
        .not_.is_("mensaje", "null")\
        .gte("creada_en", "2025-12-01")\
        .order("creada_en", desc=True)\
        .execute()
    publicaciones = response.data
    
    if not publicaciones:
        logger.info("No hay publicaciones pendientes recientes (dic 2025/ene 2026) para publicar en GBP")
        return
    
    logger.info(f"Publicaciones pendientes recientes para GBP: {len(publicaciones)}")
    
    # Estadísticas
    total_procesadas = 0
    total_publicaciones_gbp = 0
    videos_procesados = 0  # Contador de videos
    imagenes_procesadas = 0  # Contador de imágenes
    errores = 0
    
    # LOOP PRINCIPAL - Procesar cada publicación
    for pub in publicaciones:
        # Validar que pub sea un diccionario válido
        if not isinstance(pub, dict):
            logger.warning(f"Publicación inválida (no es dict): {type(pub)} - {pub}")
            continue
        
        page_id = pub.get("page_id")
        post_id = pub.get("post_id")
        
        # Convertir valores JSON a tipos esperados (str o None)
        mensaje_raw = pub.get("mensaje")
        mensaje = str(mensaje_raw) if mensaje_raw and isinstance(mensaje_raw, (str, int, float)) else None
        
        imagen_url_raw = pub.get("imagen_url")
        imagen_url = str(imagen_url_raw) if imagen_url_raw and isinstance(imagen_url_raw, str) else None
        
        imagen_local_raw = pub.get("imagen_local")
        imagen_local = str(imagen_local_raw) if imagen_local_raw and isinstance(imagen_local_raw, str) else None
        
        video_local_raw = pub.get("video_local")
        video_local = str(video_local_raw) if video_local_raw and isinstance(video_local_raw, str) else None
        
        # Validar que haya mensaje válido
        if not mensaje or not isinstance(mensaje, str) or not mensaje.strip():
            logger.warning(f"Publicación {post_id} sin mensaje válido, omitiendo")
            continue
        
        # CONTROL DE LÍMITE DE VIDEOS - verificar ANTES de procesar
        es_video_post = bool(video_local and isinstance(video_local, str) and video_local.strip())
        
        if es_video_post and videos_procesados >= MAX_VIDEOS_PER_RUN:
            logger.info(f"🎥 LÍMITE DE VIDEOS ALCANZADO ({MAX_VIDEOS_PER_RUN}). Post {post_id} (video) será procesado en la próxima ejecución.")
            continue  # Saltar este video
        
        # Priorizar video_local si existe
        if video_local and isinstance(video_local, str) and es_url_valida_para_gbp(video_local):
            media_url_valida = video_local
            logger.info(f"✅ Video válido encontrado: {video_local[:50]}...")
        elif imagen_local and isinstance(imagen_local, str) and es_url_valida_para_gbp(imagen_local):
            media_url_valida = imagen_local
            logger.info(f"✅ Contenido válido encontrado (imagen_local): {imagen_local[:50]}...")
        elif imagen_url and isinstance(imagen_url, str) and es_url_valida_para_gbp(imagen_url):
            media_url_valida = imagen_url
            logger.info(f"✅ Contenido válido encontrado (imagen_url): {imagen_url[:50]}...")
        else:
            # NO PUBLICAR si no hay contenido multimedia válido
            if video_local:
                video_preview = str(video_local)[:50] if video_local else 'None'
                logger.warning(f"❌ Video_local rechazado (inválido): {video_preview}...")
            if imagen_local:
                imagen_local_preview = str(imagen_local)[:50] if imagen_local else 'None'
                logger.warning(f"❌ Imagen_local rechazada (inválida): {imagen_local_preview}...")
            if imagen_url:
                imagen_url_preview = str(imagen_url)[:50] if imagen_url else 'None'
                logger.warning(f"❌ Imagen_url rechazada (inválida): {imagen_url_preview}...")
            
            logger.info(f"⏭️  SALTANDO publicación {post_id} - sin contenido multimedia válido")
            continue  # Saltar esta publicación

        # Si llegamos aquí, tenemos contenido multimedia válido - proceder con la publicación
        
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
            if not isinstance(pagina_data, dict):
                logger.warning(f"Datos de página inválidos: {pagina_data}")
                continue
                
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
            locations_response = supabase.table("gbp_locations").select("location_name, nombre_nora, title, store_code").eq("empresa_id", empresa_id).eq("activa", True).execute()
            
            if not locations_response.data:
                logger.warning(f"No se encontraron locaciones activas para empresa_id: {empresa_id}")
                # Marcar como publicada_gbp=True para no volver a intentar
                supabase.table("meta_publicaciones_webhook").update({"publicada_gbp": True}).eq("id", pub["id"]).execute()
                continue
            
            locaciones = locations_response.data
            logger.info(f"Locaciones activas encontradas: {len(locaciones)}")
            
            # Publicar en cada locación
            for loc in locaciones:
                if not isinstance(loc, dict):
                    logger.warning(f"Locación inválida (no es dict): {loc}")
                    continue
                    
                location_name = loc.get("location_name")
                nombre_nora = loc.get("nombre_nora", "Sistema")
                title = loc.get("title", "")
                store_code = loc.get("store_code", "")
                
                if not isinstance(nombre_nora, str):
                    nombre_nora = "Sistema"
                
                # Determinar el nombre a mostrar (prioridad: title > store_code > nombre_nora)
                nombre_display = title if title else (store_code if store_code else nombre_nora)
                
                if not location_name or not isinstance(location_name, str):
                    logger.warning(f"Locación sin location_name válido: {loc}")
                    continue
                
                try:
                    logger.info(f"Publicando en {location_name}")
                    
                    # Crear post en GBP - ahora maneja videos y fotos automáticamente
                    gbp_post = create_local_post(
                        location_name=location_name,
                        auth_header=auth_header,
                        summary=mensaje,
                        video_local=video_local,
                        imagen_local=imagen_local,
                        imagen_url=imagen_url
                    )
                    
                    # Registrar en gbp_publicaciones
                    gbp_post_name = "N/A"
                    if isinstance(gbp_post, dict):
                        gbp_post_name = gbp_post.get("name", "N/A")
                    supabase.table("gbp_publicaciones").insert({
                        "location_name": location_name,
                        "nombre_nora": nombre_nora,
                        "tipo": "FROM_FACEBOOK",
                        "estado": "publicada",
                        "gbp_post_name": gbp_post_name,
                        "contenido": mensaje,
                        "imagen_url": media_url_valida,
                        "published_at": datetime.utcnow().isoformat()
                    }).execute()
                    
                    # 🔔 NOTIFICACIÓN TELEGRAM - Publicación exitosa
                    try:
                        telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
                        mensaje_corto = mensaje[:50] + "..." if len(mensaje) > 50 else mensaje
                        
                        # Detectar tipo de contenido para emoji
                        contenido_icon = "📝"  # Default
                        if media_url_valida:
                            if video_local:
                                contenido_icon = "🎥"  # Video
                            elif any(ext in media_url_valida.lower() for ext in ['.mp4', '.mov', '.m4v', '.avi', '.webm']):
                                contenido_icon = "🎥"  # Video
                            else:
                                contenido_icon = "🖼️"  # Imagen
                        
                        # Mensaje de notificación claro y útil
                        mensaje_notif = f"""✅ Publicación exitosa en tu ubicación de Google Maps

📍 **{nombre_display}**
📝 "{mensaje_corto}"
{contenido_icon} Contenido multimedia incluido
⏰ {datetime.now().strftime('%H:%M')}"""
                        
                        # Intentar enviar con imagen si está disponible y es imagen (no video)
                        if media_url_valida and contenido_icon == "🖼️":
                            try:
                                # Enviar imagen con caption
                                telegram.enviar_imagen(media_url_valida, mensaje_notif)
                                logger.info(f"📱🖼️ Notificación con imagen enviada para {post_id} en {nombre_display}")
                            except:
                                # Si falla enviar imagen, enviar solo texto
                                telegram.enviar_mensaje(mensaje_notif)
                                logger.info(f"📱 Notificación (solo texto) enviada para {post_id} en {nombre_display}")
                        else:
                            telegram.enviar_mensaje(mensaje_notif)
                            logger.info(f"📱 Notificación enviada para {post_id} en {nombre_display} ({contenido_icon})")
                    except Exception as e:
                        logger.warning(f"⚠️ Error enviando notificación: {e}")
                    
                    total_publicaciones_gbp += 1
                    
                    # Actualizar contadores por tipo de contenido
                    if es_video_post:
                        videos_procesados += 1
                        logger.info(f"🎥 Video {videos_procesados}/{MAX_VIDEOS_PER_RUN} procesado exitosamente en {location_name}")
                        
                        # DELAY ENTRE VIDEOS - solo si no es el último video
                        if videos_procesados < MAX_VIDEOS_PER_RUN:
                            logger.info(f"⏱️  Esperando {VIDEO_DELAY_SECONDS} segundos antes del próximo video...")
                            time.sleep(VIDEO_DELAY_SECONDS)
                    else:
                        imagenes_procesadas += 1
                        logger.info(f"🖼️  Imagen procesada exitosamente en {location_name}")
                
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error publicando en {location_name}: {error_msg}")
                    
                    # Si es error 404, la ubicación no existe - marcar como inactiva
                    if "404" in error_msg and "Not Found" in error_msg:
                        logger.warning(f"Ubicación {location_name} no existe en GBP, marcando como inactiva")
                        supabase.table("gbp_locations").update({"activa": False}).eq("location_name", location_name).execute()
                    
                    # Registrar error en gbp_publicaciones
                    supabase.table("gbp_publicaciones").insert({
                        "location_name": location_name,
                        "nombre_nora": nombre_nora,
                        "tipo": "FROM_FACEBOOK",
                        "estado": "error",
                        "contenido": mensaje,
                        "imagen_url": media_url_valida or imagen_local,
                        "error_mensaje": error_msg[:500],
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
    
    logger.info(f"Job {JOB_NAME} completado.")
    logger.info(f"  📊 Publicaciones procesadas: {total_procesadas}")
    logger.info(f"  📍 Posts creados en GBP: {total_publicaciones_gbp}")
    logger.info(f"  🎥 Videos procesados: {videos_procesados}/{MAX_VIDEOS_PER_RUN}")
    logger.info(f"  🖼️  Imágenes procesadas: {imagenes_procesadas}")
    logger.info(f"  ❌ Errores: {errores}")
    
    # Crear alerta de job completado y notificar por Telegram
    try:
        mensaje_resumen = (
            f"✅ Posts Facebook → GBP sincronizados\n\n"
            f"📊 Publicaciones procesadas: {total_procesadas}\n"
            f"📍 Posts creados en GBP: {total_publicaciones_gbp}\n"
            f"🎥 Videos procesados: {videos_procesados}/{MAX_VIDEOS_PER_RUN}\n"
            f"🖼️  Imágenes procesadas: {imagenes_procesadas}\n"
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
