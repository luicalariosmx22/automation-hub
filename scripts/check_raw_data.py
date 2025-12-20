import sys
import os
sys.path.insert(0, 'c:\\Users\\luica\\OneDrive\\Desktop\\automation-hub\\src')

from datetime import date
from automation_hub.integrations.meta_ads.daily_sync_service import MetaAdsDailySyncService
import json
import requests

service = MetaAdsDailySyncService()
account_id = '482291961841607'

url = f'https://graph.facebook.com/v23.0/act_{account_id}/insights'
params = {
    'access_token': service.access_token,
    'level': 'ad',
    'breakdowns': 'publisher_platform',
    'action_breakdowns': 'action_type',
    'time_range': json.dumps({'since': '2025-12-18', 'until': '2025-12-18'}),
    'fields': ','.join(service.INSIGHT_FIELDS),
    'limit': 1
}

response = requests.get(url, params=params)
data = response.json()
if data.get('data'):
    insight = data['data'][0]
    print('📊 FIELDS DISPONIBLES EN EL INSIGHT:')
    print(json.dumps(list(insight.keys()), indent=2))
    print()
    print('📊 VALORES DE EJEMPLO:')
    for key in ['impressions', 'reach', 'clicks', 'inline_link_clicks', 'spend', 'actions']:
        if key in insight:
            val = insight[key]
            if key == 'actions':
                print(f'{key}: {len(val)} actions')
                for i, act in enumerate(val[:5]):
                    print(f'  {i+1}. {act.get("action_type")}: {act.get("value")}')
            else:
                print(f'{key}: {val}')
    
    print('\n📊 TODAS LAS ACTIONS:')
    if 'actions' in insight:
        for act in insight['actions']:
            print(f'  • {act.get("action_type")}: {act.get("value")}')
