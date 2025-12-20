"""
Script para verificar que los nuevos campos se guardaron correctamente
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
load_dotenv(root_dir / '.env')

from src.automation_hub.db.supabase_client import create_client_from_env

def verificar_nuevos_campos():
    """Verifica que los nuevos 26 campos tengan datos"""
    
    supabase = create_client_from_env()
    
    # Obtener datos recientes
    response = supabase.table('meta_ads_anuncios_daily') \
        .select('*') \
        .eq('fecha_reporte', '2025-12-18') \
        .eq('id_cuenta_publicitaria', '482291961841607') \
        .limit(5) \
        .execute()
    
    if not response.data:
        print("ERROR: No se encontraron datos")
        return
    
    print(f"\nVERIFICANDO NUEVOS CAMPOS - {len(response.data)} registros")
    print("=" * 100)
    
    # Nuevos campos a verificar
    nuevos_campos = {
        'Video': [
            'video_30_sec_watched', 'video_p25_watched', 'video_p50_watched',
            'video_p75_watched', 'video_p100_watched', 'video_avg_time_watched',
            'video_play_actions_data'
        ],
        'Conversiones': [
            'conversions_data', 'conversion_values_data',
            'website_purchase_roas_value', 'purchase_roas_value'
        ],
        'Cost Per': [
            'cost_per_inline_link_click_value', 'cost_per_unique_click_value',
            'cost_per_unique_inline_link_click_value', 'cost_per_unique_link_click_value'
        ],
        'CTR': [
            'inline_link_click_ctr_value', 'unique_link_clicks_ctr_value'
        ],
        'Recall': [
            'estimated_ad_recallers_count', 'estimated_ad_recall_rate_value'
        ],
        'Thruplay': [
            'thruplays_count', 'cost_per_thruplay_value'
        ],
        'Cost Per Actions': [
            'cost_per_action_type_data', 'cost_per_conversion_data',
            'cost_per_outbound_click_data', 'cost_per_unique_outbound_click_data'
        ]
    }
    
    for categoria, campos in nuevos_campos.items():
        print(f"\n{categoria}:")
        print("-" * 100)
        
        for campo in campos:
            # Contar cuántos registros tienen datos
            count_with_data = sum(
                1 for row in response.data 
                if row.get(campo) is not None and row.get(campo) != 0 and row.get(campo) != [] and row.get(campo) != {}
            )
            
            # Obtener muestra de datos
            muestras = []
            for row in response.data[:3]:
                val = row.get(campo)
                if val is not None and val != 0 and val != [] and val != {}:
                    if isinstance(val, (list, dict)):
                        muestras.append(f"{str(val)[:60]}...")
                    else:
                        muestras.append(str(val))
            
            if count_with_data > 0:
                muestra_str = ', '.join(muestras[:2]) if muestras else 'N/A'
                print(f"  OK {campo:45} - {count_with_data}/{len(response.data)} registros - {muestra_str}")
            else:
                print(f"  -- {campo:45} - Sin datos")
    
    print("\n" + "=" * 100)
    print("\nRESUMEN:")
    
    # Contar total de campos con datos
    total_con_datos = 0
    total_campos = sum(len(campos) for campos in nuevos_campos.values())
    
    for campos in nuevos_campos.values():
        for campo in campos:
            if any(row.get(campo) is not None and row.get(campo) != 0 and row.get(campo) != [] 
                   for row in response.data):
                total_con_datos += 1
    
    print(f"  Total campos nuevos: {total_campos}")
    print(f"  Campos con datos: {total_con_datos}")
    print(f"  Campos vacios: {total_campos - total_con_datos}")
    print(f"  Porcentaje uso: {total_con_datos / total_campos * 100:.1f}%")
    print()

if __name__ == "__main__":
    verificar_nuevos_campos()
