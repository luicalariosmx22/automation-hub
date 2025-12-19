"""
Job para sincronizar información de cuentas publicitarias de Meta Ads.
"""
import logging
import os
from datetime import datetime
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.meta_ads_cuentas_repo import (
    fetch_cuentas_activas,
    actualizar_cuenta,
    marcar_error_cuenta
)
from automation_hub.db.repositories.alertas_repo import crear_alerta

logger = logging.getLogger(__name__)

JOB_NAME = "meta_ads.cuentas.daily"


def obtener_info_cuenta_meta(cuenta_id: str, access_token: str) -> dict:
    """
    Obtiene información de una cuenta publicitaria desde Meta Ads API.
    
    Args:
        cuenta_id: ID de la cuenta publicitaria
        access_token: Token de acceso de Meta
        
    Returns:
        Diccionario con información de la cuenta
    """
    import requests
    
    # Campos a obtener de la API
    fields = [
        "name",
        "account_status",
        "currency",
        "spend_cap",
        "amount_spent",
        "balance",
        "business_name",
        "timezone_name"
    ]
    
    url = f"https://graph.facebook.com/v18.0/{cuenta_id}"
    params = {
        "access_token": access_token,
        "fields": ",".join(fields)
    }
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    return response.json()


def obtener_anuncios_activos(cuenta_id: str, access_token: str) -> int:
    """
    Cuenta los anuncios activos de una cuenta.
    
    Args:
        cuenta_id: ID de la cuenta publicitaria
        access_token: Token de acceso de Meta
        
    Returns:
        Número de anuncios activos
    """
    import requests
    
    url = f"https://graph.facebook.com/v18.0/{cuenta_id}/ads"
    params = {
        "access_token": access_token,
        "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
        "limit": 1,
        "summary": "true"
    }
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    return data.get("summary", {}).get("total_count", 0)


def run(ctx=None):
    """
    Ejecuta el job de sincronización de cuentas publicitarias.
    
    1. Obtiene token de Meta Ads
    2. Lee cuentas activas de Supabase
    3. Para cada cuenta, actualiza información desde Meta API
    4. Guarda cambios en BD
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Cargar configuración
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
        logger.warning("No se encontraron cuentas activas")
        return
    
    logger.info(f"Procesando {len(cuentas)} cuentas publicitarias")
    
    # Estadísticas
    stats = {
        "total": len(cuentas),
        "actualizadas": 0,
        "errores": 0,
        "con_cambios": 0
    }
    
    cuentas_con_error = []
    
    for cuenta in cuentas:
        cuenta_id = cuenta.get("id_cuenta_publicitaria")
        nombre = cuenta.get("nombre_cliente") or cuenta.get("nombre_cuenta") or cuenta_id
        
        if not cuenta_id:
            logger.warning(f"Cuenta sin ID: {cuenta}")
            continue
        
        try:
            logger.info(f"Procesando cuenta: {nombre}")
            
            # Obtener información de Meta API
            info_cuenta = obtener_info_cuenta_meta(cuenta_id, access_token)
            ads_activos = obtener_anuncios_activos(cuenta_id, access_token)
            
            # Preparar datos para actualizar
            datos_actualizacion = {
                "nombre_cliente": info_cuenta.get("name"),
                "account_status": info_cuenta.get("account_status"),
                "conectada": True,
                "ads_activos": ads_activos,
                "ultima_notificacion": datetime.utcnow().isoformat(),
                "ultimo_error": None,
                "ultimo_error_at": None
            }
            
            # Actualizar gasto si está disponible
            if "amount_spent" in info_cuenta:
                # Convertir de centavos a unidad monetaria
                gasto = float(info_cuenta["amount_spent"]) / 100
                datos_actualizacion["gasto_actual_mes"] = gasto
            
            # Actualizar en BD
            actualizar_cuenta(supabase, cuenta_id, datos_actualizacion)
            
            stats["actualizadas"] += 1
            stats["con_cambios"] += 1
            
            logger.info(f"✓ Cuenta {nombre} actualizada: {ads_activos} anuncios activos")
        
        except Exception as e:
            stats["errores"] += 1
            error_msg = str(e)
            
            logger.error(f"✗ Error procesando cuenta {nombre}: {error_msg}")
            
            # Marcar cuenta con error
            try:
                marcar_error_cuenta(
                    supabase,
                    cuenta_id,
                    error_msg,
                    {"job": JOB_NAME, "timestamp": datetime.utcnow().isoformat()}
                )
                
                cuentas_con_error.append({
                    "id": cuenta_id,
                    "nombre": nombre,
                    "error": error_msg
                })
            except Exception as mark_error:
                logger.error(f"No se pudo marcar error en cuenta {cuenta_id}: {mark_error}")
    
    # Resumen
    logger.info(f"Job {JOB_NAME} completado")
    logger.info(f"  Total cuentas: {stats['total']}")
    logger.info(f"  Actualizadas: {stats['actualizadas']}")
    logger.info(f"  Con errores: {stats['errores']}")
    
    # Crear alerta de job completado
    try:
        descripcion = (
            f"Se actualizaron {stats['actualizadas']} de {stats['total']} cuentas publicitarias de Meta Ads"
        )
        
        if cuentas_con_error:
            descripcion += f". {stats['errores']} cuentas con errores"
        
        crear_alerta(
            supabase=supabase,
            nombre=f"Cuentas Meta Ads Actualizadas",
            tipo="job_completado",
            nombre_nora="Sistema",
            descripcion=descripcion,
            evento_origen=JOB_NAME,
            datos={
                "total_cuentas": stats["total"],
                "actualizadas": stats["actualizadas"],
                "errores": stats["errores"],
                "cuentas_con_error": cuentas_con_error,
                "job_name": JOB_NAME
            },
            prioridad="media" if cuentas_con_error else "baja"
        )
    except Exception as e:
        logger.warning(f"No se pudo crear alerta: {e}")
