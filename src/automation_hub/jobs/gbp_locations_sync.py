"""
Job para sincronizar ubicaciones de Google Business Profile con la base de datos.
Actualiza la tabla gbp_locations con las ubicaciones activas desde la API de GBP.
"""
import logging
import requests
from datetime import datetime
from typing import List, Dict
from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.telegram.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "gbp_locations_sync"


def listar_cuentas_gbp(auth_header: dict) -> List[Dict]:
    """Lista todas las cuentas de Google Business Profile."""
    url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
    
    try:
        response = requests.get(url, headers=auth_header, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        accounts = data.get("accounts", [])
        logger.info(f"📋 Cuentas GBP encontradas: {len(accounts)}")
        return accounts
    
    except Exception as e:
        logger.error(f"❌ Error listando cuentas GBP: {e}")
        raise


def listar_ubicaciones_por_cuenta(account_name: str, auth_header: dict) -> List[Dict]:
    """Lista todas las ubicaciones de una cuenta específica."""
    url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations"
    params = {
        "readMask": "name,title,storefrontAddress,phoneNumbers,websiteUri,regularHours,categories,serviceArea,profile"
    }
    
    try:
        response = requests.get(url, headers=auth_header, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        locations = data.get("locations", [])
        return locations
    
    except Exception as e:
        logger.error(f"❌ Error listando ubicaciones para {account_name}: {e}")
        return []


def sincronizar_ubicaciones_gbp():
    """Sincroniza todas las ubicaciones de GBP a la base de datos."""
    supabase = create_client_from_env()
    auth_header = get_bearer_header()
    
    logger.info("🔄 Iniciando sincronización de ubicaciones GBP...")
    
    # Obtener cuentas
    cuentas = listar_cuentas_gbp(auth_header)
    
    total_ubicaciones = 0
    ubicaciones_nuevas = 0
    ubicaciones_actualizadas = 0
    nombres_nuevas = []  # Lista para nombres de ubicaciones nuevas
    
    for cuenta in cuentas:
        account_name = cuenta.get("name")
        account_display = cuenta.get("accountName", account_name)
        
        if not account_name:
            logger.warning(f"⚠️ Cuenta sin nombre, omitiendo: {cuenta}")
            continue
        
        logger.info(f"📍 Procesando cuenta: {account_display}")
        
        # Obtener ubicaciones de esta cuenta
        ubicaciones = listar_ubicaciones_por_cuenta(account_name, auth_header)
        
        for ubicacion in ubicaciones:
            location_name = ubicacion.get("name")
            title = ubicacion.get("title", "Sin título")
            
            # Extraer datos de la API
            storefront_address = ubicacion.get("storefrontAddress", {})
            phone_numbers = ubicacion.get("phoneNumbers", {})
            primary_phone = phone_numbers.get("primaryPhone", "") if isinstance(phone_numbers, dict) else ""
            
            # Datos de la ubicación adaptados al schema de la tabla
            ubicacion_data = {
                "location_name": location_name,
                "nombre_nora": title,  # Usar title como nombre_nora
                "title": title,
                "account_name": account_name,
                "phone": primary_phone,
                "website": ubicacion.get("websiteUri"),
                "address": storefront_address,
                "raw": ubicacion,  # Guardar todo el JSON original
                "activa": True,
                "synced_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Verificar si ya existe
            existing = supabase.table("gbp_locations").select("id").eq(
                "location_name", location_name
            ).execute()
            
            if existing.data:
                # Actualizar
                supabase.table("gbp_locations").update(ubicacion_data).eq(
                    "location_name", location_name
                ).execute()
                ubicaciones_actualizadas += 1
                logger.info(f"  ✅ Actualizada: {title}")
            else:
                # Insertar nueva
                ubicacion_data["created_at"] = datetime.utcnow().isoformat()
                supabase.table("gbp_locations").insert(ubicacion_data).execute()
                ubicaciones_nuevas += 1
                nombres_nuevas.append(title)
                logger.info(f"  ✨ Nueva: {title}")
            
            total_ubicaciones += 1
    
    logger.info(f"✅ Sincronización completada:")
    logger.info(f"  📊 Total procesadas: {total_ubicaciones}")
    logger.info(f"  ✨ Nuevas: {ubicaciones_nuevas}")
    logger.info(f"  🔄 Actualizadas: {ubicaciones_actualizadas}")
    
    return {
        "total": total_ubicaciones,
        "nuevas": ubicaciones_nuevas,
        "actualizadas": ubicaciones_actualizadas,
        "nombres_nuevas": nombres_nuevas
    }


def run():
    """
    Ejecuta el job de sincronización de ubicaciones GBP.
    """
    try:
        logger.info(f"{'=' * 60}")
        logger.info(f"🚀 Iniciando job: {JOB_NAME}")
        logger.info(f"{'=' * 60}")
        
        resultado = sincronizar_ubicaciones_gbp()
        
        # Notificación Telegram
        try:
            telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
            mensaje = (
                f"✅ <b>Sincronización GBP Locations Completada</b>\n\n"
                f"📊 Total procesadas: {resultado['total']}\n"
                f"✨ Nuevas: {resultado['nuevas']}\n"
                f"🔄 Actualizadas: {resultado['actualizadas']}"
            )
            
            # Agregar lista de nuevas ubicaciones si hay
            if resultado['nombres_nuevas']:
                mensaje += "\n\n<b>🆕 Ubicaciones nuevas:</b>\n"
                for nombre in resultado['nombres_nuevas']:
                    mensaje += f"  • {nombre}\n"
            
            telegram.enviar_mensaje(mensaje)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar notificación Telegram: {e}")
        
        logger.info(f"{'=' * 60}")
        logger.info(f"✅ Job completado: {JOB_NAME}")
        logger.info(f"{'=' * 60}")
        
    except Exception as e:
        logger.error(f"❌ Error en job {JOB_NAME}: {e}", exc_info=True)
        
        # Notificación de error
        try:
            telegram = TelegramNotifier(bot_nombre="Bot de Notificaciones")
            telegram.enviar_mensaje(
                f"❌ <b>Error en {JOB_NAME}</b>\n\n"
                f"Error: {str(e)}"
            )
        except:
            pass
        
        raise


if __name__ == "__main__":
    run()
