"""
Script para verificar tokens de Google en detalle.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def verificar_google_gbp():
    """Verifica Google OAuth (GBP)"""
    print("\n" + "="*70)
    print("🔍 GOOGLE OAUTH (GBP)")
    print("="*70)
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GBP_REFRESH_TOKEN")
    
    print(f"Client ID: {client_id[:30]}...")
    print(f"Client Secret: {client_secret[:20]}...")
    print(f"Refresh Token: {refresh_token[:30]}...")
    
    if not all([client_id, client_secret, refresh_token]):
        print("❌ Credenciales incompletas")
        return
    
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=10
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Token válido!")
            print(f"Access Token: {data.get('access_token', '')[:30]}...")
            print(f"Expires in: {data.get('expires_in')} segundos")
        else:
            print(f"\n❌ Error al refrescar token")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def verificar_google_calendar():
    """Verifica Google Calendar"""
    print("\n" + "="*70)
    print("🔍 GOOGLE CALENDAR")
    print("="*70)
    
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN")
    
    print(f"Client ID: {client_id[:30]}...")
    print(f"Client Secret: {client_secret[:20]}...")
    print(f"Refresh Token: {refresh_token[:30]}...")
    
    if not all([client_id, client_secret, refresh_token]):
        print("❌ Credenciales incompletas")
        return
    
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=10
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Token válido!")
            print(f"Access Token: {data.get('access_token', '')[:30]}...")
            print(f"Expires in: {data.get('expires_in')} segundos")
        else:
            print(f"\n❌ Error al refrescar token")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    verificar_google_gbp()
    verificar_google_calendar()
    print("\n" + "="*70)
