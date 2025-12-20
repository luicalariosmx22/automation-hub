"""
Script para probar breakdowns demográficos y geográficos de Meta Ads API
"""
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

def test_breakdown(breakdown_name, description):
    """Prueba un breakdown específico"""
    access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
    account_id = "482291961841607"
    ayer = date.today() - timedelta(days=1)
    
    url = f"https://graph.facebook.com/v23.0/act_{account_id}/insights"
    
    # Campos básicos
    fields = [
        "date_start", "date_stop", "ad_id", "ad_name",
        "impressions", "reach", "clicks", "spend"
    ]
    
    params = {
        'access_token': access_token,
        'level': 'ad',
        'breakdowns': breakdown_name,  # Un solo breakdown para probar
        'time_range': json.dumps({
            'since': ayer.strftime('%Y-%m-%d'),
            'until': ayer.strftime('%Y-%m-%d')
        }),
        'fields': ','.join(fields),
        'limit': 10,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('data'):
                print(f"\nOK: {description} (breakdown: {breakdown_name})")
                print("-" * 80)
                print(f"  Registros obtenidos: {len(data['data'])}")
                
                # Mostrar ejemplos de valores únicos
                valores_unicos = set()
                for item in data['data'][:20]:
                    val = item.get(breakdown_name)
                    if val:
                        valores_unicos.add(str(val))
                
                if valores_unicos:
                    print(f"  Valores ejemplo: {', '.join(list(valores_unicos)[:10])}")
                
                # Mostrar muestra completa del primer registro
                print(f"\n  Ejemplo completo:")
                ejemplo = data['data'][0]
                for key in sorted(ejemplo.keys()):
                    print(f"    {key}: {ejemplo[key]}")
                
                return True
            else:
                print(f"\nOK pero sin datos: {description} (breakdown: {breakdown_name})")
                return True
        else:
            error = response.json()
            print(f"\nERROR: {description} (breakdown: {breakdown_name})")
            print(f"  {error.get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\nERROR: {description} - {e}")
        return False

def main():
    """Prueba todos los breakdowns demográficos y geográficos"""
    
    print("=" * 80)
    print("PROBANDO BREAKDOWNS DEMOGRAFICOS Y GEOGRAFICOS DE META ADS API")
    print("=" * 80)
    
    breakdowns = [
        # Demográficos
        ('age', 'Edad (rangos: 18-24, 25-34, 35-44, etc.)'),
        ('gender', 'Género (male, female, unknown)'),
        
        # Geográficos
        ('country', 'País'),
        ('region', 'Región/Estado'),
        ('dma', 'DMA - Designated Market Area (ciudades USA)'),
        ('city', 'Ciudad (solo con targeting específico)'),
        
        # Dispositivo y plataforma
        ('device_platform', 'Plataforma dispositivo (mobile, desktop, etc.)'),
        ('publisher_platform', 'Plataforma publicación (facebook, instagram, etc.)'),
        ('platform_position', 'Posición en plataforma (feed, story, etc.)'),
        ('impression_device', 'Tipo de dispositivo'),
        
        # Otros
        ('product_id', 'ID de producto (para catálogos)'),
        ('hourly_stats_aggregated_by_advertiser_time_zone', 'Por hora'),
    ]
    
    resultados_ok = []
    resultados_error = []
    
    for breakdown, desc in breakdowns:
        if test_breakdown(breakdown, desc):
            resultados_ok.append((breakdown, desc))
        else:
            resultados_error.append((breakdown, desc))
        print()
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    
    print(f"\nBREAKDOWNS QUE FUNCIONAN ({len(resultados_ok)}):")
    for breakdown, desc in resultados_ok:
        print(f"  OK {breakdown:30} - {desc}")
    
    print(f"\nBREAKDOWNS QUE NO FUNCIONAN ({len(resultados_error)}):")
    for breakdown, desc in resultados_error:
        print(f"  ERROR {breakdown:30} - {desc}")
    
    # Probar combinación de breakdowns
    print("\n" + "=" * 80)
    print("PROBANDO COMBINACION: age + gender + country")
    print("=" * 80)
    test_breakdown_combinado()

def test_breakdown_combinado():
    """Prueba combinación de múltiples breakdowns"""
    access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
    account_id = "482291961841607"
    ayer = date.today() - timedelta(days=1)
    
    url = f"https://graph.facebook.com/v23.0/act_{account_id}/insights"
    
    fields = [
        "date_start", "ad_id", "ad_name",
        "impressions", "reach", "clicks", "spend"
    ]
    
    params = {
        'access_token': access_token,
        'level': 'ad',
        'breakdowns': 'age,gender,country',  # Múltiples breakdowns
        'time_range': json.dumps({
            'since': ayer.strftime('%Y-%m-%d'),
            'until': ayer.strftime('%Y-%m-%d')
        }),
        'fields': ','.join(fields),
        'limit': 20,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nOK! Registros obtenidos: {len(data.get('data', []))}")
            
            if data.get('data'):
                print("\nPrimeros 5 ejemplos:")
                for i, item in enumerate(data['data'][:5], 1):
                    print(f"\n  Registro {i}:")
                    print(f"    Ad: {item.get('ad_name', 'N/A')[:50]}")
                    print(f"    Edad: {item.get('age', 'N/A')}")
                    print(f"    Genero: {item.get('gender', 'N/A')}")
                    print(f"    Pais: {item.get('country', 'N/A')}")
                    print(f"    Impresiones: {item.get('impressions', 0)}")
                    print(f"    Alcance: {item.get('reach', 0)}")
                    print(f"    Clicks: {item.get('clicks', 0)}")
                    print(f"    Gasto: ${item.get('spend', 0)}")
        else:
            error = response.json()
            print(f"\nERROR: {error.get('error', {}).get('message', 'Unknown')}")
            
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    main()
