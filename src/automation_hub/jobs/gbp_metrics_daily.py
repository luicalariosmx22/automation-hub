"""
Job para sincronizar métricas diarias de Google Business Profile.
También sincroniza ubicaciones (nuevas, actualizadas o eliminadas).
"""
import logging
import os
import requests
from datetime import date, timedelta, datetime
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.integrations.gbp.performance_v1 import fetch_multi_daily_metrics, parse_metrics_to_rows
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.gbp_locations_repo import fetch_active_locations
from automation_hub.db.repositories.gbp_metrics_repo import upsert_metrics_daily
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram, TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "gbp.metrics.daily"


def sincronizar_ubicaciones_gbp(auth_header: dict, supabase, nombre_nora: str) -> dict:
    """
    Sincroniza ubicaciones de GBP desde la API a la base de datos.
    Envía notificación por Telegram cuando detecta nuevas ubicaciones.
    
    Returns:
        Dict con estadísticas: nuevas, actualizadas, total
    """
    logger.info("🔄 Sincronizando ubicaciones de GBP...")
    
    stats = {
        'nuevas': 0,
        'actualizadas': 0,
        'total': 0,
        'errores': 0
    }
    
    # Preparar notifier de Telegram
    telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
    
    try:
        # 1. Listar cuentas GBP
        url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
        response = requests.get(url, headers=auth_header, timeout=30)
        response.raise_for_status()
        cuentas = response.json().get("accounts", [])
        
        logger.info(f"  Cuentas GBP encontradas: {len(cuentas)}")
        
        # 2. Para cada cuenta, listar ubicaciones
        for cuenta in cuentas:
            account_name = cuenta.get("name", "")
            
            # Listar ubicaciones de la cuenta
            url_locs = f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations"
            params = {"readMask": "name,title,storefrontAddress,websiteUri,phoneNumbers,categories,latlng,openInfo,metadata,serviceArea,profile"}
            
      🔄 SINCRONIZAR UBICACIONES PRIMERO
    ubicaciones_stats = sincronizar_ubicaciones_gbp(auth_header, supabase, nombre_nora or "Sistema")
    
    # Obtener locaciones activas (ahora incluye las recién sincronizadas)
            while url_locs:
                resp = requests.get(url_locs, headers=auth_header, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                
                all_locations.extend(data.get("locations", []))
                
                next_token = data.get("nextPageToken")
                if next_token:
                    params["pageToken"] = next_token
                else:
                    url_locs = None
            
            stats['total'] += len(all_locations)
            
            # 3. Sincronizar cada ubicación
            for loc in all_locations:
                try:
                    location_name = loc.get("name", "")
                    if not location_name:
                        continue
                    
                    # Extraer datos
                    title = loc.get("title", "Sin título")
                    address = loc.get("storefrontAddress", {})
                    address_str = ", ".join(filter(None, [
                        address.get("addressLines", [""])[0] if address.get("addressLines") else "",
                        address.get("locality"),
                        address.get("administrativeArea"),
                        address.get("postalCode")
                    ]))
                    
                    phone = loc.get("phoneNumbers", {}).get("primaryPhone", "")
                    website = loc.get("websiteUri", "")
                    
                    ubicacion_data = {
                        "location_name": location_name,
                        "account_name": account_name,
                        "title": title,
                        "address": address_str or None,
                        "phone": phone or None,
                        "website_url": website or None,
                        "nombre_nora": nombre_nora,
                        "activa": True,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    # Verificar si existe
                    existing = supabase.table("gbp_locations").select("id").eq(
                        "location_name", location_name
                    ).execute()
                    
                    if existing.data and len(existing.data) > 0:
                        # Actualizar
                        supabase.table("gbp_locations").update(ubicacion_data).eq(
                            "location_name", location_name
                        ).execute()
                        stats['actualizadas'] += 1
                        logger.debug(f"  ✓ Actualizada: {title}")
                    else:
                        # Insertar nueva
                        ubicacion_data["created_at"] = datetime.utcnow().isoformat()
                        supabase.table("gbp_locations").insert(ubicacion_data).execute()
                        stats['nuevas'] += 1
                        logger.info(f"  ✅ Nueva ubicación: {title}")
                        
                        # 🔔 NOTIFICACIÓN TELEGRAM - Nueva ubicación detectada
                        try:
                            mensaje_nueva = f"""🆕 **Nueva ubicación de Google Business Profile detectada**

📍 **{title}**
🏢 Dirección: {address_str if address_str else 'N/A'}
📞 Teléfono: {phone if phone else 'N/A'}
🌐 Web: {website if website else 'N/A'}

✅ Sincronizada automáticamente
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
                            
                            telegram.enviar_mensaje(mensaje_nueva)
                            logger.info(f"  📱 Notificación enviada para nueva ubicación: {title}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Error enviando notificación de nueva ubicación: {e}")
                
                except Exception as e:
                    logger.error(f"  Error con ubicación {loc.get('name')}: {e}")
                    stats['errores'] += 1
        
        logger.info(f"✅ Ubicaciones sincronizadas - Total: {stats['total']}, Nuevas: {stats['nuevas']}, Actualizadas: {stats['actualizadas']}")
        
    except Exception as e:
        logger.error(f"Error sincronizando ubicaciones: {e}", exc_info=True)
    
    return stats


def run(ctx=None):
    """
    Ejecuta el job de sincronización de métricas diarias.
    
    1. Sincroniza ubicaciones de GBP (nuevas, actualizadas)
    2. Obtiene token de acceso de Google
    3. Lee locaciones activas de Supabase
    4. Para cada locación con location_id válido, descarga métricas
    5. Inserta/actualiza métricas en BD
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Cargar configuración desde env vars
    nombre_nora = os.getenv("GBP_NOMBRE_NORA")  # Opcional
    
    # Métricas a descargar
    metrics_csv = os.getenv("GBP_METRICS", "WEBSITE_CLICKS,CALL_CLICKS")
    metrics = [m.strip() for m in metrics_csv.split(",")]
    
    # Rango de días
    days_back = int(os.getenv("GBP_DAYS_BACK", "30"))
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    logger.info(f"Métricas a obtener: {metrics}")
    logger.info(f"Rango de fechas: {start_date} a {end_date}")
    
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
    total_metrics = 0
    
    for location in locations:
        location_name = location.get("location_name")  # Ya es locations/{id}
        nombre_nora_loc = location.get("nombre_nora") or "Sistema"
        api_id = location.get("api_id")  # Puede ser None si no existe
        
        if not location_name:
            logger.warning(f"Locación sin location_name: {location}")
            continue
        
        try:
            logger.info(f"Procesando métricas para: {location_name}")
            
            # Descargar métricas
            time_series = fetch_multi_daily_metrics(
                location_name, auth_header, metrics, start_date, end_date
            )
            
            if not time_series:
                logger.info(f"No hay métricas para {location_name}")
                continue
            
            # Parsear a formato de BD
            metrics_rows = parse_metrics_to_rows(
                time_series, nombre_nora_loc, api_id, location_name
            )
            
            if metrics_rows:
                # Insertar en BD
                upsert_metrics_daily(supabase, metrics_rows)
                total_metrics += len(metrics_rows)
                logger.info(f"Métricas procesadas para {location_name}: {len(metrics_rows)}")
        
        except Exception as e:
            # 404 es normal (locación sin acceso a Performance API)
            if "404" in str(e):
                logger.warning(f"Locación {location_name} sin acceso a Performance API (404)")
            else:
                logger.error(f"Error procesando {location_name}: {e}", exc_info=True)
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Total métricas: {total_metrics}")
    # Mensaje con ubicaciones sincronizadas
        descripcion = f"Se han sincronizado {total_metrics} métricas de {len(locations)} locaciones GBP (últimos {days_back} días)"
        
        # Agregar info de ubicaciones si hubo cambios
        if ubicaciones_stats['nuevas'] > 0 or ubicaciones_stats['actualizadas'] > 0:
            descripcion += f"\n\n📍 Ubicaciones: {ubicaciones_stats['nuevas']} nuevas, {ubicaciones_stats['actualizadas']} actualizadas"
        
        crear_alerta(
            supabase=supabase,
            nombre=f"Métricas GBP Actualizadas",
            tipo="job_completado",
            nombre_nora="Sistema",
            descripcion=descripcion,
            evento_origen=JOB_NAME,
            datos={
                "total_metricas": total_metrics,
                "total_locaciones": len(locations),
                "dias_atras": days_back,
                "fecha_inicio": str(start_date),
                "fecha_fin": str(end_date),
                "ubicaciones_nuevas": ubicaciones_stats['nuevas'],
                "ubicaciones_actualizadas": ubicaciones_stats['actualizadas'],
                "job_name": JOB_NAME
            },
            prioridad="baja"
        )
        
        # Notificar por Telegram usando bot de notificaciones
        bot_token = "8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE"
        chat_id = "5674082622"
        notifier = TelegramNotifier(bot_token=bot_token, default_chat_id=chat_id)
        
        mensaje_telegram = "📊 Métricas GBP Sincronizadas\n\n"
        mensaje_telegram += f"✅ {total_metrics} métricas procesadas\n"
        mensaje_telegram += f"📍 {len(locations)} ubicaciones activas\n"
        
        if ubicaciones_stats['nuevas'] > 0:
            mensaje_telegram += f"🆕 {ubicaciones_stats['nuevas']} ubicaciones nuevas\n"
        if ubicaciones_stats['actualizadas'] > 0:
            mensaje_telegram += f"🔄 {ubicaciones_stats['actualizadas']} ubicaciones actualizadas\n"
        
        mensaje_telegram += f"\n⏱️ Período: {days_back} días"
        
        notifier.enviar_mensaje(mensaje_telegram        "Locaciones": len(locations),
                "Período": f"{days_back} días"
            }
        )
    except Exception as e:
        logger.warning(f"No se pudo crear alerta: {e}")
