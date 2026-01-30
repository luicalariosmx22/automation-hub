"""
Job para sincronizar estado de cuentas publicitarias de Meta Ads y páginas de Facebook.
Detecta cuentas desactivadas y nuevas páginas de Facebook.
"""
import logging
import os
import requests
from datetime import datetime
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.meta_ads_cuentas_repo import (
    fetch_cuentas_activas,
    actualizar_estado_cuenta,
    registrar_error_cuenta
)
from automation_hub.integrations.meta_ads.accounts import (
    get_ad_account_info,
    get_active_ads_count
)
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram, TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "meta_ads.cuentas.sync.daily"


def enviar_alerta_whatsapp(phone: str, message: str, title: str = "Alerta"):
    """Envía una alerta por WhatsApp."""
    try:
        whatsapp_url = os.getenv("WHATSAPP_SERVER_URL", "http://192.168.68.68:3000/send-alert")
        
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


def sincronizar_paginas_facebook(access_token: str, supabase) -> dict:
    """
    Sincroniza páginas de Facebook desde la API de Meta.
    Detecta nuevas páginas y las agrega a facebook_paginas.
    
    Returns:
        Dict con estadísticas: nuevas, actualizadas, total
    """
    logger.info("🔄 Sincronizando páginas de Facebook...")
    
    stats = {
        'nuevas': 0,
        'actualizadas': 0,
        'total': 0,
        'errores': 0
    }
    
    telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
    
    try:
        # 1. Obtener usuario actual (me)
        url_me = "https://graph.facebook.com/v21.0/me"
        params = {
            'access_token': access_token,
            'fields': 'id,name'
        }
        
        response = requests.get(url_me, params=params, timeout=30)
        response.raise_for_status()
        user_data = response.json()
        user_id = user_data.get('id')
        
        logger.info(f"  Usuario: {user_data.get('name')} ({user_id})")
        
        # 2. Obtener páginas del usuario
        url_pages = f"https://graph.facebook.com/v21.0/{user_id}/accounts"
        params = {
            'access_token': access_token,
            'fields': 'id,name,access_token,category,is_published'
        }
        
        response = requests.get(url_pages, params=params, timeout=30)
        response.raise_for_status()
        pages_data = response.json()
        
        pages = pages_data.get('data', [])
        stats['total'] = len(pages)
        
        logger.info(f"  Páginas encontradas: {len(pages)}")
        
        # 3. Sincronizar cada página
        for page in pages:
            try:
                page_id = page.get('id')
                if not page_id:
                    continue
                
                page_name = page.get('name', 'Sin nombre')
                page_token = page.get('access_token', '')
                category = page.get('category', '')
                is_published = page.get('is_published', True)
                
                # Verificar si existe
                existing = supabase.table("facebook_paginas").select("id, nombre").eq(
                    "page_id", page_id
                ).execute()
                
                if existing.data and len(existing.data) > 0:
                    # Ya existe - actualizar
                    update_data = {
                        "nombre": page_name,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    supabase.table("facebook_paginas").update(update_data).eq(
                        "page_id", page_id
                    ).execute()
                    
                    stats['actualizadas'] += 1
                    logger.debug(f"  ✓ Actualizada: {page_name}")
                else:
                    # Nueva página - insertar
                    insert_data = {
                        "page_id": page_id,
                        "nombre": page_name,
                        "page_access_token": page_token,
                        "categoria": category,
                        "activa": is_published,
                        "publicar_en_gbp": False,  # Por defecto desactivado
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    supabase.table("facebook_paginas").insert(insert_data).execute()
                    
                    stats['nuevas'] += 1
                    logger.info(f"  ✅ Nueva página: {page_name}")
                    
                    # 🔔 NOTIFICACIÓN TELEGRAM - Nueva página detectada
                    try:
                        mensaje_nueva = f"""🆕 **Nueva página de Facebook detectada**

📄 **{page_name}**
🆔 ID: {page_id}
📁 Categoría: {category if category else 'N/A'}
✅ Publicada: {'Sí' if is_published else 'No'}

⚠️ **Acción requerida:** 
- Vincular a una empresa en `cliente_empresas`
- Activar `publicar_en_gbp` si se desea sincronizar con Google Business Profile

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
                        
                        telegram.enviar_mensaje(mensaje_nueva)
                        logger.info(f"  📱 Notificación enviada para nueva página: {page_name}")
                        
                        # 📱 TAMBIÉN ENVIAR POR WHATSAPP
                        whatsapp_phone = os.getenv("WHATSAPP_ALERT_PHONE", "5216629360887")
                        if whatsapp_phone:
                            enviar_alerta_whatsapp(
                                phone=whatsapp_phone,
                                title="Nueva Página Facebook",
                                message=mensaje_nueva
                            )
                    except Exception as e:
                        logger.warning(f"  ⚠️ Error enviando notificación de nueva página: {e}")
            
            except Exception as e:
                logger.error(f"  Error procesando página {page.get('name')}: {e}")
                stats['errores'] += 1
        
        logger.info(f"✅ Páginas sincronizadas - Total: {stats['total']}, Nuevas: {stats['nuevas']}, Actualizadas: {stats['actualizadas']}")
        
    except Exception as e:
        logger.error(f"Error sincronizando páginas de Facebook: {e}", exc_info=True)
    
    return stats


def run(ctx=None):
    """
    Ejecuta el job de sincronización de cuentas publicitarias y páginas de Facebook.
    
    1. Sincroniza páginas de Facebook (nuevas, actualizadas)
    2. Lee cuentas activas de Supabase
    3. Para cada cuenta, consulta su estado en Meta Ads API
    4. Detecta cambios de estado (activa → inactiva)
    5. Crea alertas cuando una cuenta se desactiva
    6. Actualiza información de anuncios activos
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Obtener configuración
    nombre_nora = os.getenv("META_ADS_NOMBRE_NORA")  # Opcional
    access_token = os.getenv("META_ADS_ACCESS_TOKEN")
    
    if not access_token:
        logger.error("META_ADS_ACCESS_TOKEN no configurado")
        return
    
    # Crear cliente Supabase
    supabase = create_client_from_env()
    
    # 1. SINCRONIZAR PÁGINAS DE FACEBOOK PRIMERO
    logger.info("=== SINCRONIZACIÓN DE PÁGINAS DE FACEBOOK ===")
    paginas_stats = sincronizar_paginas_facebook(access_token, supabase)
    
    # Obtener cuentas activas
    logger.info("=== SINCRONIZACIÓN DE CUENTAS PUBLICITARIAS ===")
    logger.info("Obteniendo cuentas publicitarias activas")
    cuentas = fetch_cuentas_activas(supabase, nombre_nora)
    
    if not cuentas:
        logger.warning("No se encontraron cuentas publicitarias activas")
        return
    
    # Estadísticas de cuentas publicitarias
    stats = {
        "total": len(cuentas),
        "sincronizadas": 0,
        "desactivadas": 0,
        "errores": 0,
        "alertas_creadas": []
    }
    
    # Procesar cada cuenta
    for cuenta in cuentas:
        id_cuenta_publicitaria = cuenta.get("id_cuenta_publicitaria")
        id_interno = cuenta.get("id")  # ID interno de la BD
        nombre_cuenta = cuenta.get("nombre_cliente") or cuenta.get("nombre_cuenta") or id_cuenta_publicitaria
        estado_anterior = cuenta.get("account_status")
        nombre_nora_cuenta = cuenta.get("nombre_nora") or "Sistema"
        empresa_nombre = cuenta.get("nombre_empresa")
        
        if not id_cuenta_publicitaria or not id_interno:
            logger.warning(f"Cuenta sin ID: {cuenta}")
            continue
        
        try:
            logger.info(f"Sincronizando cuenta: {nombre_cuenta} ({id_cuenta_publicitaria})")
            
            # Obtener info de Meta Ads API
            account_info = get_ad_account_info(id_cuenta_publicitaria, access_token)
            
            if not account_info:
                # Error al obtener info
                registrar_error_cuenta(
                    supabase, 
                    id_interno,
                    "No se pudo obtener información de la cuenta desde Meta Ads API",
                    "API_NO_RESPONSE"
                )
                stats["errores"] += 1
                continue
            
            # Extraer estado actual
            account_status = account_info.get("account_status", 0)
            
            # Obtener cantidad de anuncios activos
            ads_activos = get_active_ads_count(id_cuenta_publicitaria, access_token)
            
            # Actualizar en BD
            actualizar_estado_cuenta(
                supabase,
                id_interno,  # ID interno (int)
                account_status,
                ads_activos
            )
            stats["sincronizadas"] += 1
            
            # Detectar si la cuenta fue desactivada
            if estado_anterior == 1 and account_status != 1:
                logger.warning(f"¡Cuenta DESACTIVADA detectada! {nombre_cuenta} ({id_cuenta_publicitaria})")
                stats["desactivadas"] += 1
                
                # Crear alerta de alta prioridad
                try:
                    alerta_id = crear_alerta(
                        supabase=supabase,
                        nombre=f"⚠️ Cuenta Publicitaria Desactivada",
                        tipo="cuenta_desactivada",
                        nombre_nora=nombre_nora_cuenta,
                        descripcion=f"La cuenta publicitaria '{nombre_cuenta}'{f' de {empresa_nombre}' if empresa_nombre else ''} ha sido DESACTIVADA. Esto puede deberse a problemas de pago o incumplimiento de políticas.",
                        evento_origen=JOB_NAME,
                        datos={
                            "id_cuenta": id_cuenta_publicitaria,
                            "nombre_cuenta": nombre_cuenta,
                            "empresa_nombre": empresa_nombre,
                            "estado_anterior": estado_anterior,
                            "estado_actual": account_status,
                            "ads_activos_antes": cuenta.get("ads_activos"),
                            "moneda": account_info.get("currency"),
                            "job_name": JOB_NAME
                        },
                        prioridad="alta"
                    )
                    stats["alertas_creadas"].append({
                        "cuenta": nombre_cuenta,
                        "alerta_id": alerta_id
                    })
                    
                    # Enviar notificación por Telegram
                    notificar_alerta_telegram(
                        nombre="🚨 Cuenta Meta Ads Desactivada",
                        descripcion=f"La cuenta '{nombre_cuenta}'{f' de {empresa_nombre}' if empresa_nombre else ''} ha sido DESACTIVADA.\n\nEsto puede deberse a:\n• Problemas de pago\n• Incumplimiento de políticas\n• Límites de gasto alcanzados",
                        prioridad="alta",
                        datos={
                            "Cuenta": nombre_cuenta,
                            "ID": id_cuenta_publicitaria,
                            "Cliente": empresa_nombre or "N/A",
                            "Estado Anterior": "Activa" if estado_anterior == 1 else f"Inactiva ({estado_anterior})",
                            "Estado Actual": account_status
                        },
                        nombre_nora=nombre_nora_cuenta,
                        job_name=JOB_NAME,
                        tipo_alerta="cuenta_desactivada"
                    )
                    
                    # 📱 TAMBIÉN ENVIAR POR WHATSAPP
                    whatsapp_phone = os.getenv("WHATSAPP_ALERT_PHONE", "5216629360887")
                    if whatsapp_phone:
                        mensaje_whatsapp = f"""🚨 Cuenta Meta Ads Desactivada

📊 {nombre_cuenta}
🏢 {empresa_nombre or 'N/A'}
🆔 {id_cuenta_publicitaria}

⚠️ Esto puede deberse a:
• Problemas de pago
• Incumplimiento de políticas
• Límites de gasto alcanzados

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
                        
                        enviar_alerta_whatsapp(
                            phone=whatsapp_phone,
                            title="🚨 Cuenta Desactivada",
                            message=mensaje_whatsapp
                        )
                except Exception as e:
                    logger.error(f"Error creando alerta para {nombre_cuenta}: {e}")
            
            # Log si la cuenta estaba inactiva y sigue inactiva
            elif estado_anterior != 1 and account_status != 1:
                logger.info(f"Cuenta {nombre_cuenta} sigue inactiva (status={account_status})")
            
            # Log si la cuenta se reactivó
            elif estado_anterior != 1 and account_status == 1:
                logger.info(f"✓ Cuenta {nombre_cuenta} fue REACTIVADA")
        
        except Exception as e:
            logger.error(f"Error procesando cuenta {nombre_cuenta}: {e}", exc_info=True)
            stats["errores"] += 1
            
            try:
                registrar_error_cuenta(
                    supabase,
                    id_interno,
                    str(e),
                    type(e).__name__
                )
            except Exception as reg_error:
                logger.error(f"Error registrando error: {reg_error}")
    
    # Resumen final
    logger.info(f"Job {JOB_NAME} completado")
    logger.info(f"Total cuentas: {stats['total']}")
    logger.info(f"Sincronizadas: {stats['sincronizadas']}")
    logger.info(f"Desactivadas detectadas: {stats['desactivadas']}")
    logger.info(f"Errores: {stats['errores']}")
    
    # Crear alerta de resumen si hubo cambios
    if stats['sincronizadas'] > 0 or paginas_stats.get('nuevas', 0) > 0:
        try:
            descripcion = f"Sincronización completada: {stats['sincronizadas']} cuentas actualizadas"
            
            if paginas_stats.get('nuevas', 0) > 0:
                descripcion += f", 🆕 {paginas_stats['nuevas']} páginas nuevas de Facebook"
            
            if stats['desactivadas'] > 0:
                descripcion += f", ⚠️ {stats['desactivadas']} cuentas DESACTIVADAS detectadas"
            
            if stats['errores'] > 0:
                descripcion += f", {stats['errores']} errores"
            
            prioridad = "media" if stats['desactivadas'] > 0 else "baja"
            
            crear_alerta(
                supabase=supabase,
                nombre=f"Sincronización de Cuentas Meta Ads",
                tipo="job_completado",
                nombre_nora="Sistema",
                descripcion=descripcion,
                evento_origen=JOB_NAME,
                datos={
                    **stats,
                    "paginas_nuevas": paginas_stats.get('nuevas', 0),
                    "paginas_actualizadas": paginas_stats.get('actualizadas', 0),
                    "job_name": JOB_NAME
                },
                prioridad=prioridad
            )
            
            # Notificación por Telegram del resumen
            mensaje_resumen = f"📊 Sync Meta Ads completado\n\n"
            mensaje_resumen += f"✅ {stats['sincronizadas']} cuentas sincronizadas\n"
            
            if paginas_stats.get('nuevas', 0) > 0:
                mensaje_resumen += f"🆕 {paginas_stats['nuevas']} páginas nuevas\n"
            if paginas_stats.get('actualizadas', 0) > 0:
                mensaje_resumen += f"🔄 {paginas_stats['actualizadas']} páginas actualizadas\n"
            if stats['desactivadas'] > 0:
                mensaje_resumen += f"⚠️ {stats['desactivadas']} cuentas desactivadas\n"
            if stats['errores'] > 0:
                mensaje_resumen += f"❌ {stats['errores']} errores\n"
            
            telegram = TelegramNotifier(bot_nombre="Bot Principal")
            telegram.enviar_mensaje(mensaje_resumen)
            
        except Exception as e:
            logger.warning(f"No se pudo crear alerta de resumen: {e}")
