import requests, json, os
from dotenv import load_dotenv
load_dotenv()

token = os.getenv('META_ACCESS_REDACTED_TOKEN')
url = 'https://graph.facebook.com/v23.0/act_482291961841607/insights'

fields_list = [
    'ad_id', 'date_start', 'date_stop', 'account_id', 'campaign_id', 'adset_id',
    'ad_name', 'adset_name', 'campaign_name',
    'impressions', 'reach', 'clicks', 'inline_link_clicks', 'spend',
    'ctr', 'cpc', 'cpm', 'frequency',
    'unique_clicks', 'unique_inline_link_clicks', 'unique_ctr',
    'actions',
    'outbound_clicks', 'outbound_clicks_ctr',
    'thruplays',
    'website_ctr'
]

params = {
    'access_token': token,
    'level': 'ad',
    'breakdowns': 'publisher_platform',
    'action_breakdowns': 'action_type',
    'action_attribution_windows': '1d_view,7d_click',
    'time_range': json.dumps({'since': '2025-12-12', 'until': '2025-12-12'}, separators=(',', ':')),
    'fields': ','.join(fields_list),
    'limit': 5
}

print('Testing fields:', ','.join(fields_list))
print()
r = requests.get(url, params=params)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'✅ Success! Anuncios: {len(data.get("data", []))}')
    if data.get('data'):
        print(f'First ad: {json.dumps(data["data"][0], indent=2)[:500]}')
else:
    print(f'❌ Error: {r.text[:500]}')
