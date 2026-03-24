"""
Job para publicar posts de Facebook a Google Business Profile.
"""
import logging
import time
from datetime import datetime
from typing import Optional

import requests

from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.posts_v1 import create_local_post
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import TelegramNotifier
from automation_hub.config.settings import load_settings, Settings

logger = logging.getLogger(__name__)

JOB_NAME = "meta_to_gbp_daily"
MAX_VIDEOS_PER_RUN = 10  # Máximo videos por ejecución
VIDEO_DELAY_SECONDS = 120  # 2 minutos de delay entre videos
DEFAULT_WHATSAPP_URL = "http://192.168.68.68:3000/send-alert"
DEFAULT_WHATSAPP_ALERT_PHONE = "5216629360887"


def enviar_alerta_whatsapp(
    phone: str,
    message: str,
    title: str = "Alerta",
    settings: Optional[Settings] = None,
):
    """Envía una alerta por WhatsApp."""
    try:
        settings_obj = settings or load_settings()
        whatsapp_url = settings_obj.whatsapp.server_url or DEFAULT_WHATSAPP_URL

        payload = {
            "phone": phone,
            "title": title,
            "message": message
        }
        
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(whatsapp_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"📱 WhatsApp enviado a {phone}")
            return True
        else:
            logger.warning(f"⚠️  Error enviando WhatsApp: {response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️  Error enviando WhatsApp: {e}")
        return False
def build_full_location_name(account_name: Optional[str], location_name: Optional[str], location_id: Optional[str] = None) -> str:
    """
    Devuelve el resource name correcto para GBP posts:
    accounts/*/locations/*
    
    Evita duplicación cuando location_name ya viene completo desde la API.
    """
    if not location_name:
        return ""

    # Caso ideal: ya viene completo desde la API (accounts/.../locations/...)
    if isinstance(location_name, str) and location_name.startswith("accounts/") and "/locations/" in location_name:
        logger.debug(f"✅ location_name ya completo: {location_name}")
        return location_name

    # Si te llega "locations/123" y tienes account_name
    if account_name and isinstance(location_name, str) and location_name.startswith("locations/"):
        full = f"{account_name}/{location_name}"
        logger.debug(f"✅ Construido desde locations/: {full}")
        return full

    # Si te llega solo el id "123" y tienes ambos
    if account_name and location_id:
        full = f"{account_name}/locations/{location_id}"
        logger.debug(f"✅ Construido desde location_id: {full}")
        return full

    # Último recurso: devolver tal cual
    logger.warning(f"⚠️  No se pudo construir full_location_name correctamente: {location_name}")
    return location_name


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
    settings = load_settings()
    
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
        
        # Rechazar imagen_url si NO es de Supabase Storage (puede tener tokens, redirects, etc.)
        if imagen_url and not es_url_valida_para_gbp(imagen_url):
            logger.debug(f"❌ Imagen_url rechazada (no es Supabase): {imagen_url[:60]}...")
            imagen_url = None
        
        imagen_local_raw = pub.get("imagen_local")
        imagen_local = str(imagen_local_raw) if imagen_local_raw and isinstance(imagen_local_raw, str) else None
        
        # Rechazar imagen_local si NO es de Supabase Storage
        if imagen_local and 'supabase.co/storage/v1/object/public' not in imagen_local:
            logger.debug(f"❌ Imagen_local rechazada (no es Supabase): {imagen_local[:60]}...")
            imagen_local = None
        
        video_local_raw = pub.get("video_local")
        video_local = str(video_local_raw) if video_local_raw and isinstance(video_local_raw, str) else None
        
        # Rechazar video_local si NO es de Supabase Storage
        if video_local and 'supabase.co/storage/v1/object/public' not in video_local:
            logger.debug(f"❌ Video_local rechazado (no es Supabase): {video_local[:60]}...")
            video_local = None
        
        # Validar que haya mensaje válido
        if not mensaje or not isinstance(mensaje, str) or not mensaje.strip():
            logger.warning(f"Publicación {post_id} sin mensaje válido, omitiendo")
            continue
        
        # CONTROL DE LÍMITE DE VIDEOS - verificar ANTES de procesar
        es_video_post = bool(video_local and isinstance(video_local, str) and video_local.strip())
        
        if es_video_post and videos_procesados >= MAX_VIDEOS_PER_RUN:
            logger.info(f"🎥 LÍMITE DE VIDEOS ALCANZADO ({MAX_VIDEOS_PER_RUN}). Post {post_id} (video) será procesado en la próxima ejecución.")
            continue  # Saltar este video
        
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
            
            # Obtener locaciones activas de esa empresa (IMPORTANTE: incluir account_name y location_id)
            locations_response = supabase.table("gbp_locations").select("account_name, location_name, location_id, nombre_nora, title, store_code").eq("empresa_id", empresa_id).eq("activa", True).execute()
            
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
                    
                account_name = loc.get("account_name")
                location_name = loc.get("location_name")
                location_id = loc.get("location_id")
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
                
                # Construir el nombre completo usando el helper (evita duplicación)
                full_location_name = build_full_location_name(
                    str(account_name) if account_name else None,
                    str(location_name) if location_name else None,
                    str(location_id) if location_id else None,
                )
                
                if not full_location_name:
                    logger.warning(f"No se pudo construir full_location_name para: {loc}")
                    continue
                
                # LOG para validar que no hay duplicación
                logger.info(f"📍 account_name={account_name} | location_name={location_name} | full={full_location_name}")
                
                # Determinar qué media se usó ANTES de intentar publicar
                media_usado = video_local or imagen_local or imagen_url
                
                try:
                    logger.info(f"Publicando en {full_location_name}...")
                    if video_local:
                        logger.info(f"  Con video: {video_local[:80]}...")
                    elif imagen_local:
                        logger.info(f"  Con imagen_local: {imagen_local[:80]}...")
                    elif imagen_url:
                        logger.info(f"  Con imagen_url: {imagen_url[:80]}...")
                    
                    # Crear post en GBP - usar nombre completo con account
                    gbp_post = create_local_post(
                        location_name=full_location_name,
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
                        "location_name": full_location_name,
                        "nombre_nora": nombre_nora,
                        "tipo": "FROM_FACEBOOK",
                        "estado": "publicada",
                        "gbp_post_name": gbp_post_name,
                        "contenido": mensaje,
                        "imagen_url": media_usado,
                        "published_at": datetime.utcnow().isoformat()
                    }).execute()
                    
                    # 🔔 NOTIFICACIÓN TELEGRAM - Publicación exitosa
                    try:
                        telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
                        mensaje_corto = mensaje[:50] + "..." if len(mensaje) > 50 else mensaje
                        
                        # Detectar tipo de contenido para emoji
                        contenido_icon = "📝"  # Default
                        if media_usado:
                            if video_local:
                                contenido_icon = "🎥"  # Video
                            elif any(ext in media_usado.lower() for ext in ['.mp4', '.mov', '.m4v', '.avi', '.webm']):
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
                        if media_usado and contenido_icon == "🖼️":
                            try:
                                # Enviar imagen con caption
                                telegram.enviar_imagen(media_usado, mensaje_notif)
                                logger.info(f"📱🖼️ Notificación con imagen enviada para {post_id} en {nombre_display}")
                            except:
                                # Si falla enviar imagen, enviar solo texto
                                telegram.enviar_mensaje(mensaje_notif)
                                logger.info(f"📱 Notificación (solo texto) enviada para {post_id} en {nombre_display}")
                        else:
                            telegram.enviar_mensaje(mensaje_notif)
                            logger.info(f"📱 Notificación enviada para {post_id} en {nombre_display} ({contenido_icon})")
                        
                        # 📱 TAMBIÉN ENVIAR POR WHATSAPP
                        whatsapp_phone = settings.whatsapp.alert_phone or DEFAULT_WHATSAPP_ALERT_PHONE
                        if whatsapp_phone:
                            enviar_alerta_whatsapp(
                                phone=whatsapp_phone,
                                title=f"Google Maps - {nombre_display}",
                                message=mensaje_notif,
                                settings=settings,
                            )
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
                    logger.error(f"Error publicando en {full_location_name}: {error_msg}")
                    
                    # Solo marcar como inactiva si:
                    # 1. El error es 404 Not Found
                    # 2. El location_name ya es formato completo (accounts/.../locations/...)
                    # 3. El full_location_name coincide con location_name (no fue construido)
                    # Esto evita desactivar por errores de construcción del path
                    if "404" in error_msg and "Not Found" in error_msg:
                        es_formato_completo = (
                            isinstance(location_name, str) and 
                            location_name.startswith("accounts/") and 
                            "/locations/" in location_name
                        )
                        
                        if es_formato_completo and full_location_name == location_name:
                            logger.warning(f"⚠️  Ubicación {full_location_name} no existe en GBP (404 confirmado), marcando como inactiva")
                            supabase.table("gbp_locations").update({"activa": False}).eq("location_name", location_name).execute()
                        else:
                            logger.warning(f"⚠️  Error 404 en {full_location_name}, pero no se marca inactiva (posible error de construcción)")
                            logger.warning(f"   location_name={location_name} | full={full_location_name} | formato_completo={es_formato_completo}")
                    
                    # Registrar error en gbp_publicaciones
                    supabase.table("gbp_publicaciones").insert({
                        "location_name": full_location_name,
                        "nombre_nora": nombre_nora,
                        "tipo": "FROM_FACEBOOK",
                        "estado": "error",
                        "contenido": mensaje,
                        "imagen_url": media_usado,
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
