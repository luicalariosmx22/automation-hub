"""
Script para actualizar todas las ubicaciones de GBP desde la API.
Sincroniza las ubicaciones desde Google Business Profile a la base de datos.
"""
import os
import sys
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.integrations.google.oauth import get_bearer_header
from automation_hub.db.supabase_client import create_client_from_env

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def listar_cuentas_gbp(auth_header: dict) -> List[Dict]:
    """
    Lista todas las cuentas de Google Business Profile.
    
    Args:
        auth_header: Header de autorización
        
    Returns:
        Lista de cuentas
    """
    url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
    
    try:
        response = requests.get(url, headers=auth_header, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        accounts = data.get("accounts", [])
        logger.info(f"Cuentas GBP encontradas: {len(accounts)}")
        return accounts
    
    except Exception as e:
        logger.error(f"Error listando cuentas GBP: {e}")
        raise


def listar_ubicaciones_cuenta(account_name: str, auth_header: dict) -> List[Dict]:
    """
    Lista todas las ubicaciones de una cuenta GBP.
    
    Args:
        account_name: Nombre de la cuenta (formato: accounts/*)
        auth_header: Header de autorización
        
    Returns:
        Lista de ubicaciones
    """
    url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations"
    params = {
        "readMask": "name,title,storefrontAddress,websiteUri,phoneNumbers,categories,latlng,openInfo,metadata,serviceArea,profile"
    }
    
    all_locations = []
    
    try:
        while url:
            response = requests.get(url, headers=auth_header, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            locations = data.get("locations", [])
            all_locations.extend(locations)
            
            # Paginación
            next_page_token = data.get("nextPageToken")
            if next_page_token:
                params["pageToken"] = next_page_token
            else:
                url = None
        
        logger.info(f"  Ubicaciones encontradas en {account_name}: {len(all_locations)}")
        return all_locations
    
    except Exception as e:
        logger.error(f"Error listando ubicaciones de {account_name}: {e}")
        return []


def extraer_datos_ubicacion(location: Dict, account_name: str) -> Dict:
    """
    Extrae los datos relevantes de una ubicación.
    
    Args:
        location: Datos de la ubicación desde la API
        account_name: Nombre de la cuenta
        
    Returns:
        Dict con datos procesados
    """
    # Extraer location_name y location_id
    location_name = location.get("name", "")
    location_id = location_name.split("/")[-1] if "/" in location_name else None
    
    # Extraer dirección
    address = location.get("storefrontAddress", {})
    
    # Extraer coordenadas
    latlng = location.get("latlng", {})
    lat = latlng.get("latitude")
    lng = latlng.get("longitude")
    
    # Extraer teléfono principal
    phone_numbers = location.get("phoneNumbers", {})
    primary_phone = phone_numbers.get("primaryPhone")
    additional_phones = phone_numbers.get("additionalPhones", [])
    
    # Extraer categorías
    categories = location.get("categories", {})
    primary_category = categories.get("primaryCategory", {}).get("displayName")
    additional_categories = [cat.get("displayName") for cat in categories.get("additionalCategories", [])]
    
    # Extraer metadata
    metadata = location.get("metadata", {})
    place_id = metadata.get("placeId")
    maps_uri = metadata.get("mapsUri")
    duplicate_location = metadata.get("duplicateLocation", False)
    canonical_id = metadata.get("canonicalName", "").split("/")[-1] if metadata.get("canonicalName") else None
    
    # Extraer profile info
    profile = location.get("profile", {})
    description = profile.get("description")
    
    return {
        "account_name": account_name,
        "location_name": location_name,
        "location_id": location_id,
        "title": location.get("title"),
        "primary_category": primary_category,
        "phone": primary_phone,
        "website": location.get("websiteUri"),
        "address": address if address else None,
        "lat": lat,
        "lng": lng,
        "open_info": location.get("openInfo"),
        "state": location.get("locationState", {}).get("locationState"),
        "metadata": metadata if metadata else None,
        "raw": location,
        "additional_phones": additional_phones if additional_phones else None,
        "categories": {
            "primary": primary_category,
            "additional": additional_categories
        } if (primary_category or additional_categories) else None,
        "description": description,
        "service_area": location.get("serviceArea"),
        "special_hours": None,  # No disponible en v1
        "more_hours": location.get("moreHours"),
        "place_id": place_id,
        "maps_uri": maps_uri,
        "duplicate_location": duplicate_location,
        "canonical_id": canonical_id,
        "synced_at": datetime.utcnow().isoformat()
    }


def actualizar_ubicacion_db(supabase, ubicacion_data: Dict, nombre_nora: str) -> bool:
    """
    Actualiza o inserta una ubicación en la base de datos.
    
    Args:
        supabase: Cliente de Supabase
        ubicacion_data: Datos de la ubicación
        nombre_nora: Nombre del tenant
        
    Returns:
        True si se actualizó correctamente
    """
    try:
        # Verificar si ya existe
        existing = supabase.table("gbp_locations").select("id").eq(
            "location_id", ubicacion_data["location_id"]
        ).eq("nombre_nora", nombre_nora).execute()
        
        # Agregar nombre_nora
        ubicacion_data["nombre_nora"] = nombre_nora
        ubicacion_data["updated_at"] = datetime.utcnow().isoformat()
        
        if existing.data:
            # Actualizar
            result = supabase.table("gbp_locations").update(ubicacion_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
            logger.info(f"  ✓ Actualizada: {ubicacion_data['title']}")
        else:
            # Insertar
            ubicacion_data["created_at"] = datetime.utcnow().isoformat()
            result = supabase.table("gbp_locations").insert(ubicacion_data).execute()
            logger.info(f"  ✓ Nueva: {ubicacion_data['title']}")
        
        return True
    
    except Exception as e:
        logger.error(f"  ✗ Error con {ubicacion_data.get('title', 'N/A')}: {e}")
        return False


def actualizar_ubicaciones_gbp(nombre_nora: Optional[str] = None):
    """
    Actualiza todas las ubicaciones de GBP desde la API.
    
    Args:
        nombre_nora: Nombre del tenant (si es None, se usa el de la variable de entorno)
    """
    # Cargar variables de entorno
    load_dotenv()
    
    if not nombre_nora:
        nombre_nora = os.getenv("NOMBRE_NORA", "").strip()
        if not nombre_nora:
            raise ValueError("NOMBRE_NORA no configurado en variables de entorno")
    
    print("\n" + "="*60)
    print("ACTUALIZACIÓN DE UBICACIONES GBP")
    print("="*60)
    print(f"Tenant: {nombre_nora}\n")
    
    # Obtener credenciales
    print("🔑 Obteniendo credenciales de GBP...")
    try:
        auth_header = get_bearer_header()
        print("✓ Credenciales obtenidas\n")
    except Exception as e:
        print(f"❌ Error obteniendo credenciales: {e}")
        return
    
    # Conectar a Supabase
    print("🔌 Conectando a Supabase...")
    try:
        supabase = create_client_from_env()
        print("✓ Conexión establecida\n")
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        return
    
    # Listar cuentas
    print("📋 Listando cuentas de GBP...")
    try:
        cuentas = listar_cuentas_gbp(auth_header)
        print(f"✓ {len(cuentas)} cuenta(s) encontrada(s)\n")
    except Exception as e:
        print(f"❌ Error listando cuentas: {e}")
        return
    
    # Procesar cada cuenta
    total_ubicaciones = 0
    total_actualizadas = 0
    
    for cuenta in cuentas:
        account_name = cuenta.get("name", "")
        account_display_name = cuenta.get("accountName", account_name)
        
        print(f"📍 Procesando cuenta: {account_display_name}")
        print(f"   ID: {account_name}")
        
        # Listar ubicaciones de la cuenta
        ubicaciones = listar_ubicaciones_cuenta(account_name, auth_header)
        total_ubicaciones += len(ubicaciones)
        
        # Procesar cada ubicación
        for ubicacion in ubicaciones:
            try:
                datos = extraer_datos_ubicacion(ubicacion, account_name)
                if actualizar_ubicacion_db(supabase, datos, nombre_nora):
                    total_actualizadas += 1
            except Exception as e:
                logger.error(f"  ✗ Error procesando ubicación: {e}")
        
        print()
    
    # Resumen
    print("="*60)
    print("RESUMEN")
    print("="*60)
    print(f"Total de cuentas procesadas: {len(cuentas)}")
    print(f"Total de ubicaciones encontradas: {total_ubicaciones}")
    print(f"Total de ubicaciones actualizadas: {total_actualizadas}")
    
    if total_actualizadas > 0:
        print(f"\n✅ Actualización completada exitosamente")
    else:
        print(f"\n⚠️  No se actualizó ninguna ubicación")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Actualizar ubicaciones de GBP")
    parser.add_argument(
        "--nombre-nora",
        help="Nombre del tenant (si no se especifica, se usa NOMBRE_NORA del .env)",
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        actualizar_ubicaciones_gbp(args.nombre_nora)
    except KeyboardInterrupt:
        print("\n\n⚠️  Actualización cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Error inesperado")
        sys.exit(1)
