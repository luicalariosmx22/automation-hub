"""Script rápido para ver qué campos funcionan"""
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

CAMPOS_EXTRAS = [
    # Video metrics avanzados
    "video_30_sec_watched_actions",
    "video_p25_watched_actions",
    "video_p50_watched_actions", 
    "video_p75_watched_actions",
    "video_p100_watched_actions",
    "video_avg_time_watched_actions",
    "video_play_actions",
    
    # Conversiones
    "conversions",
    "conversion_values",
    "website_purchase_roas",
    "purchase_roas",
    
    # Cost per metrics
    "cost_per_inline_link_click",
    "cost_per_inline_post_engagement",
    "cost_per_unique_click",
    "cost_per_unique_inline_link_click",
    "cost_per_action_type",
    "cost_per_conversion",
    "cost_per_outbound_click",
    "cost_per_unique_outbound_click",
    "cost_per_thruplay",
    
    # Otros
    "estimated_ad_recallers",
    "estimated_ad_recall_rate",
    "video_thruplay_watched_actions",
    "unique_link_clicks_ctr",
    "cost_per_unique_link_click",
    "inline_link_click_ctr",
]

def test_all_at_once():
    """Prueba todos los campos juntos"""
    access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
    account_id = "482291961841607"
    ayer = date.today() - timedelta(days=1)
    
    campos_base = [
        "date_start", "date_stop", "account_id", "campaign_id", "adset_id", "ad_id",
        "ad_name", "adset_name", "campaign_name",
        "impressions", "reach", "clicks", "inline_link_clicks",
        "spend", "cpm", "cpc", "ctr", "unique_ctr",
        "actions", "action_values",
        "unique_clicks", "unique_inline_link_clicks",
        "outbound_clicks", "outbound_clicks_ctr",
        "website_ctr"
    ]
    
    url = f"https://graph.facebook.com/v23.0/act_{account_id}/insights"
    params = {
        'access_token': access_token,
        'level': 'ad',
        'breakdowns': 'publisher_platform',
        'action_breakdowns': 'action_type',
        'time_range': json.dumps({
            'since': ayer.strftime('%Y-%m-%d'),
            'until': ayer.strftime('%Y-%m-%d')
        }),
        'fields': ','.join(campos_base + CAMPOS_EXTRAS),
        'limit': 1,
    }
    
    print(f"Probando {len(CAMPOS_EXTRAS)} campos adicionales...")
    print("=" * 80)
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nOK! Todos los {len(CAMPOS_EXTRAS)} campos funcionan!")
            print("\nLista de campos que podemos agregar:")
            print("=" * 80)
            for campo in sorted(CAMPOS_EXTRAS):
                print(f"  - {campo}")
            
            # Ver qué trae datos
            if data.get('data'):
                sample = data['data'][0]
                print(f"\nCampos con datos en la muestra:")
                print("=" * 80)
                for campo in CAMPOS_EXTRAS:
                    if campo in sample and sample[campo]:
                        print(f"  + {campo}: {sample[campo]}")
        else:
            print(f"ERROR {response.status_code}")
            print(response.json())
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_all_at_once()
