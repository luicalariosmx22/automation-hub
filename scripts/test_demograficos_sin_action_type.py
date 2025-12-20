"""Prueba combinación demográfica SIN action_type"""
import os
import sys
import json
import requests
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
load_dotenv(root_dir / '.env')

access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
account_id = "482291961841607"
ayer = date.today() - timedelta(days=1)

url = f"https://graph.facebook.com/v23.0/act_{account_id}/insights"

# Sin action_breakdowns, solo demográficos
params = {
    'access_token': access_token,
    'level': 'ad',
    'breakdowns': 'age',  # Solo edad
    # NO incluir 'action_breakdowns' para evitar incompatibilidad
    'time_range': json.dumps({
        'since': ayer.strftime('%Y-%m-%d'),
        'until': ayer.strftime('%Y-%m-%d')
    }),
    'fields': 'ad_id,ad_name,impressions,reach,clicks,spend,cpm,cpc,ctr',
    'limit': 20,
}

print("PROBANDO: age + gender + region (SIN action_type)")
print("=" * 80)

print(f"\nURL: {url}")
print(f"Params: {json.dumps({k: v for k, v in params.items() if k != 'access_token'}, indent=2)}\n")

response = requests.get(url, params=params, timeout=30)

if response.status_code == 200:
    data = response.json()
    print(f"\nOK! Registros: {len(data.get('data', []))}")
    
    if data.get('data'):
        print("\nPrimeros 5 registros:\n")
        for i, item in enumerate(data['data'][:5], 1):
            print(f"Registro {i}:")
            print(f"  Ad: {item.get('ad_name', 'N/A')[:50]}")
            print(f"  Edad: {item.get('age', 'N/A')}")
            print(f"  Genero: {item.get('gender', 'N/A')}")
            print(f"  Region: {item.get('region', 'N/A')}")
            print(f"  Impresiones: {item.get('impressions', 0)}")
            print(f"  Clicks: {item.get('clicks', 0)}")
            print(f"  Gasto: ${item.get('spend', 0)}")
            
            # Ver si actions viene
            if item.get('actions'):
                print(f"  Actions: {len(item['actions'])} acciones")
                for action in item['actions'][:3]:
                    print(f"    - {action.get('action_type')}: {action.get('value')}")
            print()
else:
    print(f"ERROR {response.status_code}")
    print(response.json())
