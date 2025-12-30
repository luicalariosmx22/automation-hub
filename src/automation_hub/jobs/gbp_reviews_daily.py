"""
Job para sincronizar reviews diarias de Google Business Profile.
"""
import logging
import os
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.reviews_v4 import list_all_reviews, map_review_to_row
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.gbp_locations_repo import fetch_active_locations
from automation_hub.db.repositories.gbp_reviews_repo import upsert_reviews
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram, TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "gbp.reviews.daily"


def run(ctx=None):
    """
    Ejecuta el job de sincronización de reviews diarias.
    
    1. Obtiene token de acceso de Google
    2. Lee locaciones activas de Supabase
    3. Para cada locación, descarga reviews
    4. Inserta/actualiza reviews en BD
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Cargar configuración desde env vars
    nombre_nora = os.getenv("GBP_NOMBRE_NORA")  # Opcional
    
    # Obtener header de autorización (valida OAuth internamente)
    logger.info("Obteniendo credenciales de Google OAuth")
    auth_header = get_bearer_header()
    
    # Crear cliente Supabase (valida variables internamente)
    supabase = create_client_from_env()
    
    # Obtener locaciones activas
    logger.info("Obteniendo locaciones activas")
    locations = fetch_active_locations(supabase, nombre_nora)
    
    if not locations:
        logger.warning("No se encontraron locaciones activas")
        return
    
    # Procesar cada locación
    total_nuevas = 0
    total_replies = 0
    locaciones_con_nuevas = []
    locaciones_con_replies = []
    total_malas_nuevas = 0
    locaciones_con_malas = []
    reviews_malas_detalle = []  # Para almacenar info detallada de reviews malas
    
    for location in locations:
        account_name = location.get("account_name")
        location_name = location.get("location_name")
        nombre_nora_loc = location.get("nombre_nora") or "Sistema"
        api_id = location.get("api_id")  # Puede ser None si no existe
        location_title = location.get("title") or location_name.split("/")[-1]
        
        if not account_name or not location_name:
            logger.warning(f"Locación sin account_name o location_name: {location}")
            continue
        
        # Construir parent path completo: accounts/{account_id}/locations/{location_id}
        parent_location_name = f"{account_name}/{location_name}"
        
        try:
            logger.info(f"Procesando reviews para: {parent_location_name}")
            
            # Descargar reviews
            reviews_raw = list_all_reviews(parent_location_name, auth_header)
            
            if not reviews_raw:
                logger.info(f"No hay reviews para {parent_location_name}")
                continue
            
            # Mapear reviews a formato de BD
            reviews_mapped = [
                map_review_to_row(review, nombre_nora_loc or "", api_id, parent_location_name)
                for review in reviews_raw
            ]
            
            # Verificar cuáles son nuevas y cuáles tienen replies nuevos
            nuevas_reviews = []
            reviews_con_reply_nuevo = []
            malas_nuevas_locacion = 0
            
            for review_data in reviews_mapped:
                # Buscar si ya existe en BD
                existing = supabase.table("gbp_reviews").select("review_id, reply_comment").eq(
                    "location_name", parent_location_name
                ).eq("review_id", review_data["review_id"]).execute()
                
                if not existing.data:
                    # Review nueva
                    nuevas_reviews.append(review_data)
                    
                    # Verificar si es mala reseña (1-2 estrellas) y guardar detalles
                    star_rating = review_data.get("star_rating")
                    if star_rating and star_rating <= 2:
                        malas_nuevas_locacion += 1
                        
                        # Guardar información detallada de la review mala
                        location_id = parent_location_name.split('/')[-1]  # Extraer location ID
                        review_mala = {
                            "ubicacion": location_title,
                            "ubicacion_nora": nombre_nora_loc,
                            "rating": star_rating,
                            "autor": review_data.get("reviewer_display_name", "Anónimo"),
                            "texto": review_data.get("comment", "Sin comentario")[:150] + "..." if len(review_data.get("comment", "")) > 150 else review_data.get("comment", "Sin comentario"),
                            "fecha": review_data.get("create_time", ""),
                            "review_id": review_data.get("review_id"),
                            "location_api_path": parent_location_name,
                            "link_contestar": f"https://business.google.com/dashboard/l/{location_id}",
                            "link_reviews": f"https://business.google.com/dashboard/l/{location_id}/reviews"
                        }
                        reviews_malas_detalle.append(review_mala)
                else:
                    # Review existente - solo actualizar si hay reply nuevo
                    old_reply = existing.data[0].get("reply_comment")
                    new_reply = review_data.get("reply_comment")
                    
                    if new_reply and new_reply != old_reply:
                        reviews_con_reply_nuevo.append(review_data)
            
            # Insertar reviews nuevas
            if nuevas_reviews:
                supabase.table("gbp_reviews").insert(nuevas_reviews).execute()
                total_nuevas += len(nuevas_reviews)
                locaciones_con_nuevas.append({
                    "nombre": location_title,
                    "cantidad": len(nuevas_reviews),
                    "nora": nombre_nora_loc
                })
                logger.info(f"✨ {len(nuevas_reviews)} reviews NUEVAS en {location_title}")
                
                # Contar malas reviews nuevas
                if malas_nuevas_locacion > 0:
                    total_malas_nuevas += malas_nuevas_locacion
                    locaciones_con_malas.append({
                        "nombre": location_title,
                        "cantidad": malas_nuevas_locacion,
                        "nora": nombre_nora_loc
                    })
                    logger.warning(f"⚠️ {malas_nuevas_locacion} reviews MALAS (1-2 estrellas) en {location_title}")
            
            # Actualizar reviews con reply nuevo
            if reviews_con_reply_nuevo:
                for review_data in reviews_con_reply_nuevo:
                    supabase.table("gbp_reviews").update(review_data).eq(
                        "location_name", parent_location_name
                    ).eq("review_id", review_data["review_id"]).execute()
                
                total_replies += len(reviews_con_reply_nuevo)
                locaciones_con_replies.append({
                    "nombre": location_title,
                    "cantidad": len(reviews_con_reply_nuevo),
                    "nora": nombre_nora_loc
                })
                logger.info(f"💬 {len(reviews_con_reply_nuevo)} respuestas NUEVAS en {location_title}")
        
        except Exception as e:
            # 404 es normal (locación sin acceso a Reviews API v4)
            if "404" in str(e):
                logger.warning(f"Locación {parent_location_name} sin acceso a Reviews API (404)")
            else:
                logger.error(f"Error procesando {parent_location_name}: {e}", exc_info=True)
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Nuevas: {total_nuevas}, Replies: {total_replies}, Malas nuevas: {total_malas_nuevas}")
    
    # Crear alerta de job completado y notificar por Telegram
    try:
        # Construir descripción con detalle
        descripcion_partes = []
        if total_nuevas > 0:
            descripcion_partes.append(f"🆕 {total_nuevas} reviews nuevas")
        if total_replies > 0:
            descripcion_partes.append(f"💬 {total_replies} respuestas nuevas")
        if total_malas_nuevas > 0:
            descripcion_partes.append(f"⚠️ {total_malas_nuevas} reviews MALAS")
        
        if not descripcion_partes:
            descripcion_partes.append("Sin cambios")
        
        descripcion = " | ".join(descripcion_partes)
        
        # Datos detallados
        datos_alerta = {
            "total_nuevas": total_nuevas,
            "total_replies": total_replies,
            "total_malas_nuevas": total_malas_nuevas,
            "total_locaciones": len(locations),
            "job_name": JOB_NAME
        }
        
        if locaciones_con_nuevas:
            datos_alerta["locaciones_nuevas"] = locaciones_con_nuevas
        if locaciones_con_replies:
            datos_alerta["locaciones_replies"] = locaciones_con_replies
        if locaciones_con_malas:
            datos_alerta["locaciones_malas"] = locaciones_con_malas
        if reviews_malas_detalle:
            datos_alerta["reviews_malas_detalle"] = reviews_malas_detalle
        
        # Determinar prioridad según contenido
        prioridad = "alta" if total_malas_nuevas > 0 else "baja"
        
        crear_alerta(
            supabase=supabase,
            nombre=f"Reviews GBP Actualizadas",
            tipo="job_completado",
            nombre_nora="Sistema",
            descripcion=descripcion,
            evento_origen=JOB_NAME,
            datos=datos_alerta,
            prioridad=prioridad
        )
        
        # Notificar por Telegram con detalle
        datos_telegram = {
            "Reviews Nuevas": total_nuevas,
            "Respuestas Nuevas": total_replies,
            "Locaciones Procesadas": len(locations)
        }
        
        if total_malas_nuevas > 0:
            datos_telegram["⚠️ REVIEWS MALAS"] = total_malas_nuevas
        
        # Agregar detalle de locaciones con nuevas
        if locaciones_con_nuevas:
            locaciones_str = ", ".join([f"{loc['nombre']} ({loc['cantidad']})" for loc in locaciones_con_nuevas[:5]])
            if len(locaciones_con_nuevas) > 5:
                locaciones_str += f" y {len(locaciones_con_nuevas) - 5} más"
            datos_telegram["Nuevas en"] = locaciones_str
        
        # Agregar detalle de locaciones con replies
        if locaciones_con_replies:
            replies_str = ", ".join([f"{loc['nombre']} ({loc['cantidad']})" for loc in locaciones_con_replies[:5]])
            if len(locaciones_con_replies) > 5:
                replies_str += f" y {len(locaciones_con_replies) - 5} más"
            datos_telegram["Respuestas en"] = replies_str
        
        # Agregar detalle de locaciones con malas reviews
        if locaciones_con_malas:
            malas_str = ", ".join([f"{loc['nombre']} ({loc['cantidad']})" for loc in locaciones_con_malas[:5]])
            if len(locaciones_con_malas) > 5:
                malas_str += f" y {len(locaciones_con_malas) - 5} más"
            datos_telegram["🚨 Malas en"] = malas_str
        
        # Agregar información detallada de reviews malas para Telegram
        if reviews_malas_detalle:
            mensaje_reviews_malas = "📋 REVIEWS MALAS DETECTADAS:\n\n"
            for i, review in enumerate(reviews_malas_detalle[:3]):  # Máximo 3 para no sobrecargar
                mensaje_reviews_malas += f"🏢 {review['ubicacion']} ({review['ubicacion_nora']})\n"
                mensaje_reviews_malas += f"⭐ {review['rating']} estrellas - {review['autor']}\n"
                mensaje_reviews_malas += f"💬 \"{review['texto']}\"\n"
                mensaje_reviews_malas += f"� {review['fecha'][:10] if review['fecha'] else 'Fecha no disponible'}\n"
                mensaje_reviews_malas += f"🔗 Dashboard: {review['link_contestar']}\n"
                mensaje_reviews_malas += f"📝 Reviews: {review['link_reviews']}\n"
                if i < len(reviews_malas_detalle[:3]) - 1:
                    mensaje_reviews_malas += "\n---\n\n"
            
            if len(reviews_malas_detalle) > 3:
                mensaje_reviews_malas += f"\n... y {len(reviews_malas_detalle) - 3} reviews malas más"
                
            datos_telegram["Detalle Reviews Malas"] = mensaje_reviews_malas
        
        # Notificar por Telegram usando bot de notificaciones
        bot_token = "8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE"
        chat_id = "5674082622"
        notifier = TelegramNotifier(bot_token=bot_token, default_chat_id=chat_id)
        
        # Determinar ícono y prioridad para Telegram
        if total_malas_nuevas > 0:
            icono = "🚨"
            prioridad_telegram = "alta"
        elif total_nuevas > 0 or total_replies > 0:
            icono = "✅"
            prioridad_telegram = "media"
        else:
            icono = "✅"
            prioridad_telegram = "baja"
        
        notifier.enviar_alerta(
            nombre=f"{icono} Reviews GBP Sincronizadas",
            descripcion=descripcion,
            prioridad=prioridad_telegram,
            datos=datos_telegram
        )
    except Exception as e:
        logger.warning(f"No se pudo crear alerta: {e}")
