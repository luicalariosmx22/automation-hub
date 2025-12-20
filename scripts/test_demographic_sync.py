"""
Script para probar la sincronización demográfica de Meta Ads
"""
import os
import sys
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Agregar root al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Cargar .env
load_dotenv(root_dir / '.env')

from src.automation_hub.integrations.meta_ads.demographic_sync_service import (
    MetaAdsDemographicSyncService
)
from src.automation_hub.db.supabase_client import create_client_from_env

def test_demographic_sync():
    """Prueba la sincronización demográfica"""
    
    # Cuenta de prueba
    account_id = "482291961841607"
    fecha = date(2025, 12, 18)  # Fecha con datos existentes
    
    print("=" * 80)
    print("PRUEBA: Sincronización Demográfica Meta Ads")
    print("=" * 80)
    print(f"Cuenta: {account_id}")
    print(f"Fecha: {fecha}")
    print("=" * 80)
    
    # Crear servicio
    service = MetaAdsDemographicSyncService()
    
    # Probar cada breakdown
    breakdowns = ['age', 'gender', 'region', 'device_platform']
    
    for breakdown in breakdowns:
        print(f"\nProbando breakdown: {breakdown}")
        print("-" * 80)
        
        # Obtener insights
        insights = service.get_demographic_insights(account_id, fecha, breakdown)
        
        if insights:
            print(f"  OK Obtenidos {len(insights)} insights")
            
            # Mostrar ejemplos
            valores_unicos = set()
            for insight in insights[:10]:
                val = insight.get(breakdown)
                if val:
                    valores_unicos.add(val)
            
            print(f"  Valores únicos: {', '.join(list(valores_unicos)[:5])}")
            
            # Actualizar en BD
            updated = service.update_demographic_data(
                account_id, fecha, breakdown, insights
            )
            print(f"  Registros actualizados: {updated}")
        else:
            print(f"  Sin datos para {breakdown}")
    
    # Verificar datos guardados
    print("\n" + "=" * 80)
    print("VERIFICANDO DATOS GUARDADOS")
    print("=" * 80)
    
    supabase = create_client_from_env()
    response = supabase.table('meta_ads_anuncios_daily') \
        .select('ad_id,nombre_anuncio,age,gender,region,device_platform,impresiones') \
        .eq('fecha_reporte', fecha.isoformat()) \
        .eq('id_cuenta_publicitaria', account_id) \
        .limit(10) \
        .execute()
    
    if response.data:
        print(f"\nMuestra de {len(response.data)} registros:\n")
        for i, row in enumerate(response.data[:5], 1):
            print(f"Registro {i}:")
            print(f"  Ad: {row.get('nombre_anuncio', 'N/A')[:50]}")
            print(f"  Edad: {row.get('age', 'N/A')}")
            print(f"  Género: {row.get('gender', 'N/A')}")
            print(f"  Región: {row.get('region', 'N/A')}")
            print(f"  Device: {row.get('device_platform', 'N/A')}")
            print(f"  Impressions: {row.get('impresiones', 0)}")
            print()
    else:
        print("ERROR: No se encontraron registros")
    
    print("=" * 80)

if __name__ == "__main__":
    test_demographic_sync()
