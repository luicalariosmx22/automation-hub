#!/usr/bin/env python3
"""
Test simple para verificar si una ubicación GBP específica funciona con el formato correcto
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.integrations.google.oauth import get_bearer_header

def main():
    print("🧪 TEST: Verificar si el problema es el formato de URL")
    print()
    
    try:
        # Obtener token de autorización
        auth_header = get_bearer_header()
        print("✅ Token de autorización obtenido")
        
        # Test 1: Obtener account ID
        import requests
        url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
        
        response = requests.get(url, headers=auth_header, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            accounts = data.get("accounts", [])
            
            if accounts:
                print(f"✅ Cuentas encontradas: {len(accounts)}")
                
                for account in accounts[:3]:  # Solo mostrar primeras 3
                    account_name = account.get("name", "")
                    print(f"   📁 Account: {account_name}")
                    
                    # Test 2: Obtener ubicaciones de esta cuenta
                    locations_url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations"
                    params = {"readMask": "name,title"}
                    
                    loc_response = requests.get(locations_url, headers=auth_header, params=params, timeout=30)
                    
                    if loc_response.status_code == 200:
                        loc_data = loc_response.json()
                        locations = loc_data.get("locations", [])
                        print(f"   📍 Ubicaciones: {len(locations)}")
                        
                        if locations:
                            # Mostrar formato correcto de la primera ubicación
                            first_location = locations[0]
                            location_name = first_location.get("name", "")
                            title = first_location.get("title", "Sin título")
                            
                            print(f"   ✅ Ejemplo de formato correcto:")
                            print(f"      Location name: {location_name}")
                            print(f"      Title: {title}")
                            print(f"      URL posts sería: https://mybusiness.googleapis.com/v4/{location_name}/localPosts")
                            break
                    else:
                        print(f"   ❌ Error obteniendo ubicaciones: {loc_response.status_code}")
                        
            else:
                print("❌ No se encontraron cuentas")
        else:
            print(f"❌ Error obteniendo cuentas: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print()
    print("🎯 Si ves ubicaciones con formato 'accounts/XXXX/locations/YYYY', ese es el formato correcto")
    print("   Si las tuyas están guardadas como solo 'locations/YYYY', hay que corregirlas")

if __name__ == "__main__":
    main()