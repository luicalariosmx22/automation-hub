"""
Script para sincronizar todos los anuncios de ayer
"""
import os
import sys
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Setup
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / 'src'))
load_dotenv(root_dir / '.env')

from automation_hub.integrations.meta_ads.daily_sync_service import MetaAdsDailySyncService
from automation_hub.db.supabase_client import create_client_from_env
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def sync_all_yesterday():
    """Sincroniza todas las cuentas para ayer"""
    
    fecha = date.today() - timedelta(days=1)
    
    print("=" * 80)
    print("SINCRONIZACION META ADS - TODAS LAS CUENTAS")
    print("=" * 80)
    print(f"Fecha: {fecha}")
    print("=" * 80)
    
    # Obtener cuentas activas
    supabase = create_client_from_env()
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_cuenta,nombre_nora') \
        .eq('activo', True) \
        .eq('estado_actual', 'ACTIVE') \
        .execute()
    
    cuentas = response.data or []
    print(f"\nCuentas activas: {len(cuentas)}\n")
    
    # Sincronizar cada cuenta
    service = MetaAdsDailySyncService()
    
    total_procesados = 0
    total_errores = 0
    
    for i, cuenta in enumerate(cuentas, 1):
        account_id = cuenta['id_cuenta_publicitaria']
        nombre = cuenta.get('nombre_cuenta', 'N/A')
        nora = cuenta.get('nombre_nora', '')
        
        print(f"[{i}/{len(cuentas)}] {nombre} ({account_id})...", end=' ')
        
        try:
            result = service.sync_account_daily(
                account_id=account_id,
                fecha_reporte=fecha,
                nombre_nora=nora
            )
            
            if result.get('ok'):
                procesados = result.get('processed', 0)
                total_procesados += procesados
                print(f"OK - {procesados} anuncios")
            else:
                total_errores += 1
                print(f"ERROR")
                
        except Exception as e:
            total_errores += 1
            print(f"ERROR: {str(e)[:50]}")
    
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Cuentas procesadas: {len(cuentas)}")
    print(f"Total anuncios: {total_procesados}")
    print(f"Errores: {total_errores}")
    print("=" * 80)

if __name__ == "__main__":
    sync_all_yesterday()
