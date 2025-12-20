#!/usr/bin/env python3
"""
Comparar los parámetros exactos entre lo que funciona y lo que no
"""

import os
import json
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
account_id = '482291961841607'
fecha = '2025-12-12'

# Lo que FUNCIONA (del test directo)
params_working = {
    'access_token': access_token,
    'level': 'ad',
    'breakdowns': 'publisher_platform',
    'action_breakdowns': 'action_type',
    'action_attribution_windows': '1d_view,7d_click',
    'time_range': json.dumps({'since': fecha, 'until': fecha}),
    'fields': 'ad_id,impressions,spend,actions',
    'limit': 5,
}

# Lo que NO funciona (del servicio)
INSIGHT_FIELDS = [
    "ad_id", "date_start", "date_stop", "account_id", "campaign_id", "adset_id",
    "ad_name", "adset_name", "campaign_name",
    "impressions", "reach", "clicks", "link_clicks", "inline_link_clicks", "spend",
    "ctr", "cpc", "cpm", "frequency",
    "unique_clicks", "unique_inline_link_clicks", "unique_impressions", "unique_ctr",
    "messaging_conversations_started", "cost_per_messaging_conversation_started",
    "actions"
]

params_not_working = {
    'access_token': access_token,
    'level': 'ad',
    'breakdowns': 'publisher_platform',
    'action_breakdowns': 'action_type',
    'action_attribution_windows': '1d_view,7d_click',
    'time_range': json.dumps({'since': fecha, 'until': fecha}, separators=(',', ':')),
    'fields': ','.join(INSIGHT_FIELDS),
    'limit': 500,
}

url = f"https://graph.facebook.com/v23.0/act_{account_id}/insights"

print("🧪 Probando parámetros que FUNCIONAN:")
print(f"Fields: {params_working['fields']}")
try:
    response = requests.get(url, params=params_working, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Éxito! Anuncios: {len(data.get('data', []))}")
    else:
        print(f"❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"❌ Exception: {str(e)}")

print("\n" + "="*80)
print("🧪 Probando parámetros que NO FUNCIONAN:")
print(f"Fields ({len(INSIGHT_FIELDS)}): {params_not_working['fields'][:100]}...")
try:
    response = requests.get(url, params=params_not_working, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Éxito! Anuncios: {len(data.get('data', []))}")
        if data.get('data'):
            print("\n📊 Primer anuncio:")
            print(json.dumps(data['data'][0], indent=2)[:500])
    else:
        error_data = response.json()
        print(f"❌ Error: {error_data}")
except Exception as e:
    print(f"❌ Exception: {str(e)}")

# Probar agregando fields uno por uno
print("\n" + "="*80)
print("🔍 Probando fields individuales para encontrar el problemático:")

base_fields = ['ad_id', 'impressions', 'spend']
problem_fields = []

for field in INSIGHT_FIELDS:
    if field in base_fields:
        continue
    
    test_fields = base_fields + [field]
    params_test = {
        'access_token': access_token,
        'level': 'ad',
        'breakdowns': 'publisher_platform',
        'action_breakdowns': 'action_type',
        'action_attribution_windows': '1d_view,7d_click',
        'time_range': json.dumps({'since': fecha, 'until': fecha}, separators=(',', ':')),
        'fields': ','.join(test_fields),
        'limit': 1,
    }
    
    try:
        response = requests.get(url, params=params_test, timeout=10)
        if response.status_code != 200:
            problem_fields.append(field)
            print(f"   ❌ {field}: {response.status_code}")
        else:
            print(f"   ✅ {field}")
    except Exception as e:
        problem_fields.append(field)
        print(f"   ❌ {field}: {str(e)[:50]}")

if problem_fields:
    print(f"\n⚠️ Fields problemáticos: {problem_fields}")
else:
    print(f"\n✅ Todos los fields funcionan individualmente")
