"""
Script para probar qué campos adicionales están disponibles en Meta Ads API
con los breakdowns actuales (publisher_platform y action_type)
"""
import os
import sys
import json
import requests
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Agregar root al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Cargar .env
load_dotenv(root_dir / '.env')

# Lista extendida de campos a probar
CAMPOS_EXTRAS = [
    # Status fields
    "effective_status",
    "configured_status",
    
    # Video metrics avanzados
    "video_30_sec_watched_actions",
    "video_p25_watched_actions",
    "video_p50_watched_actions", 
    "video_p75_watched_actions",
    "video_p100_watched_actions",
    "video_avg_time_watched_actions",
    "video_play_actions",
    "video_continuous_2_sec_watched_actions",
    "video_play_curve_actions",
    
    # Conversiones
    "conversions",
    "conversion_values",
    "website_purchase_roas",
    "purchase_roas",
    
    # Quality
    "quality_score_organic",
    "quality_score_ectr",
    "quality_score_ecvr",
    "engagement_rate_ranking",
    "conversion_rate_ranking",
    
    # Cost per metrics
    "cost_per_inline_link_click",
    "cost_per_inline_post_engagement",
    "cost_per_unique_click",
    "cost_per_unique_inline_link_click",
    "cost_per_unique_action_type",
    "cost_per_action_type",
    "cost_per_conversion",
    "cost_per_outbound_click",
    "cost_per_unique_outbound_click",
    "cost_per_thruplay",
    
    # Engagement avanzado
    "post_engagement",
    "page_engagement",
    "engagement_rate",
    "social_spend",
    
    # Frequency y reach
    "frequency",
    "unique_impressions",
    
    # Link y landing
    "inline_link_click_ctr",
    "unique_link_clicks_ctr",
    "cost_per_unique_link_click",
    
    # Estimated ad recall
    "estimated_ad_recallers",
    "estimated_ad_recall_rate",
    "cost_per_estimated_ad_recaller",
    
    # Thruplay
    "video_thruplay_watched_actions",
    
    # Otros
    "canvas_avg_view_time",
    "canvas_avg_view_percent",
]

def test_fields():
    """Prueba qué campos están disponibles"""
    
    access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
    account_id = "482291961841607"  # Cuenta de prueba
    
    if not access_token:
        print("ERROR: META_ACCESS_REDACTED_TOKEN no encontrado")
        return
    
    # Fecha de ayer
    ayer = date.today() - timedelta(days=1)
    
    # URL base
    url = f"https://graph.facebook.com/v23.0/act_{account_id}/insights"
    
    # Campos actuales que sabemos que funcionan
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
    
    print("PROBANDO CAMPOS ADICIONALES DE META ADS API")
    print("=" * 100)
    print(f"Cuenta: {account_id}")
    print(f"Fecha: {ayer}")
    print("=" * 100)
    
    campos_ok = []
    campos_error = []
    
    # Probar campos en lotes pequeños
    batch_size = 5
    for i in range(0, len(CAMPOS_EXTRAS), batch_size):
        batch = CAMPOS_EXTRAS[i:i+batch_size]
        campos_test = campos_base + batch
        
        params = {
            'access_token': access_token,
            'level': 'ad',
            'breakdowns': 'publisher_platform',
            'action_breakdowns': 'action_type',
            'time_range': json.dumps({
                'since': ayer.strftime('%Y-%m-%d'),
                'until': ayer.strftime('%Y-%m-%d')
            }),
            'fields': ','.join(campos_test),
            'limit': 1,
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                # Todos los campos del batch funcionan
                campos_ok.extend(batch)
                print(f"  OK Batch {i//batch_size + 1}: {', '.join(batch)}")
            else:
                # Algún campo del batch falló, probar uno por uno
                error_data = response.json()
                print(f"  WARN Batch {i//batch_size + 1} fallo, probando individualmente...")
                
                for campo in batch:
                    params_individual = params.copy()
                    params_individual['fields'] = ','.join(campos_base + [campo])
                    
                    try:
                        resp_individual = requests.get(url, params=params_individual, timeout=30)
                        
                        if resp_individual.status_code == 200:
                            campos_ok.append(campo)
                            print(f"     OK {campo}")
                        else:
                            campos_error.append(campo)
                            print(f"     ERROR {campo}")
                    except Exception as e:
                        campos_error.append(campo)
                        print(f"     ERROR {campo} - Error: {e}")
        
        except Exception as e:
            print(f"  ERROR Batch {i//batch_size + 1} - Error: {e}")
            campos_error.extend(batch)
    
    # Resumen
    print("\n" + "=" * 100)
    print(f"\nCAMPOS QUE FUNCIONAN ({len(campos_ok)}):")
    print("=" * 100)
    for campo in sorted(campos_ok):
        print(f"  - {campo}")
    
    print(f"\nCAMPOS QUE NO FUNCIONAN ({len(campos_error)}):")
    print("=" * 100)
    for campo in sorted(campos_error):
        print(f"  - {campo}")
    
    print("\n" + "=" * 100)
    print(f"\nRESUMEN:")
    print(f"  Total probados: {len(CAMPOS_EXTRAS)}")
    print(f"  Funcionan: {len(campos_ok)}")
    print(f"  No funcionan: {len(campos_error)}")
    print(f"  Porcentaje exito: {len(campos_ok) / len(CAMPOS_EXTRAS) * 100:.1f}%")
    print()

if __name__ == "__main__":
    test_fields()
