#!/usr/bin/env python3
"""
Script de prueba directa a la API de Meta para diagnosticar el error 400
"""

import os
import json
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# Obtener token
access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
if not access_token:
    print("❌ No se encontró META_ACCESS_REDACTED_TOKEN")
    exit(1)

# Cuenta de prueba
account_id = '482291961841607'  # Sin el prefijo act_
fecha = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')

print(f"🔍 Probando API de Meta Ads")
print(f"📊 Cuenta: act_{account_id}")
print(f"📅 Fecha: {fecha}")
print("="*80)

# Prueba 1: Sin attribution windows (básico)
print("\n1️⃣ Prueba básica SIN action_attribution_windows:")
url = f"https://graph.facebook.com/v23.0/act_{account_id}/insights"
params = {
    'access_token': access_token,
    'level': 'ad',
    'time_range': json.dumps({'since': fecha, 'until': fecha}),
    'fields': 'ad_id,impressions,spend',
    'limit': 5,
}

try:
    response = requests.get(url, params=params, timeout=30)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Éxito! Anuncios encontrados: {len(data.get('data', []))}")
        if data.get('data'):
            print(f"   Primer anuncio: {data['data'][0]}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Exception: {str(e)}")

# Prueba 2: Con publisher_platform breakdown
print("\n2️⃣ Prueba CON publisher_platform breakdown:")
params2 = {
    'access_token': access_token,
    'level': 'ad',
    'breakdowns': 'publisher_platform',
    'time_range': json.dumps({'since': fecha, 'until': fecha}),
    'fields': 'ad_id,impressions,spend',
    'limit': 5,
}

try:
    response = requests.get(url, params=params2, timeout=30)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Éxito! Anuncios encontrados: {len(data.get('data', []))}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Exception: {str(e)}")

# Prueba 3: Con action_breakdowns
print("\n3️⃣ Prueba CON action_breakdowns:")
params3 = {
    'access_token': access_token,
    'level': 'ad',
    'breakdowns': 'publisher_platform',
    'action_breakdowns': 'action_type',
    'time_range': json.dumps({'since': fecha, 'until': fecha}),
    'fields': 'ad_id,impressions,spend,actions',
    'limit': 5,
}

try:
    response = requests.get(url, params=params3, timeout=30)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Éxito! Anuncios encontrados: {len(data.get('data', []))}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Exception: {str(e)}")

# Prueba 4: Con action_attribution_windows (como nora)
print("\n4️⃣ Prueba CON action_attribution_windows:")
params4 = {
    'access_token': access_token,
    'level': 'ad',
    'breakdowns': 'publisher_platform',
    'action_breakdowns': 'action_type',
    'action_attribution_windows': '1d_view,7d_click',
    'time_range': json.dumps({'since': fecha, 'until': fecha}),
    'fields': 'ad_id,impressions,spend,actions',
    'limit': 5,
}

try:
    response = requests.get(url, params=params4, timeout=30)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Éxito! Anuncios encontrados: {len(data.get('data', []))}")
        if data.get('data'):
            print(f"\n   📊 Ejemplo de datos:")
            print(json.dumps(data['data'][0], indent=2)[:500])
    else:
        print(f"   ❌ Error: {response.text[:300]}")
except Exception as e:
    print(f"   ❌ Exception: {str(e)}")

# Prueba 5: Verificar si la cuenta tiene anuncios activos
print("\n5️⃣ Verificando anuncios activos en la cuenta:")
ads_url = f"https://graph.facebook.com/v23.0/act_{account_id}/ads"
ads_params = {
    'access_token': access_token,
    'fields': 'id,name,status,effective_status',
    'limit': 10,
}

try:
    response = requests.get(ads_url, params=ads_params, timeout=30)
    if response.status_code == 200:
        data = response.json()
        ads = data.get('data', [])
        print(f"   ✅ Anuncios en cuenta: {len(ads)}")
        for ad in ads[:5]:
            print(f"      • {ad.get('name', 'Sin nombre')} - Status: {ad.get('status')} / {ad.get('effective_status')}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Exception: {str(e)}")

print("\n" + "="*80)
print("✅ Diagnóstico completo")
