"""
Job para sincronizar estado de cuentas publicitarias de Meta Ads.
Detecta cuentas que han sido desactivadas y crea alertas.
"""
import logging
import os
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
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram

logger = logging.getLogger(__name__)

JOB_NAME = "meta_ads.cuentas.sync.daily"


def run(ctx=None):
    """
    Ejecuta el job de sincronización de cuentas publicitarias.
    
    1. Lee cuentas activas de Supabase
    2. Para cada cuenta, consulta su estado en Meta Ads API
    3. Detecta cambios de estado (activa → inactiva)
    4. Crea alertas cuando una cuenta se desactiva
    5. Actualiza información de anuncios activos
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
    
    # Obtener cuentas activas
    logger.info("Obteniendo cuentas publicitarias activas")
    cuentas = fetch_cuentas_activas(supabase, nombre_nora)
    
    if not cuentas:
        logger.warning("No se encontraron cuentas publicitarias activas")
        return
    
    # Estadísticas
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
    
    # Crear alerta de resumen y notificación Telegram
    if stats['desactivadas'] > 0 or stats['errores'] > 0:
        try:
            descripcion = f"Sincronización completada: {stats['sincronizadas']} cuentas actualizadas"
            
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
                    "job_name": JOB_NAME
                },
                prioridad=prioridad
            )
            
            # Notificación por Telegram del resumen
            notificar_alerta_telegram(
                nombre="📊 Resumen: Sync Cuentas Meta Ads",
                descripcion=descripcion,
                prioridad=prioridad,
                datos={
                    "Total Cuentas": stats['total'],
                    "Sincronizadas": stats['sincronizadas'],
                    "Desactivadas": stats['desactivadas'],
                    "Errores": stats['errores']
                },
                nombre_nora="Sistema",
                job_name=JOB_NAME,
                tipo_alerta="job_completado"
            )
        except Exception as e:
            logger.warning(f"No se pudo crear alerta de resumen: {e}")
