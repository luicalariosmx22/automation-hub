"""
Job para sincronizar datos demográficos de Meta Ads.
Se ejecuta DESPUÉS del job meta_ads_cuentas_sync_daily para
complementar los datos con información demográfica y geográfica.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from src.automation_hub.integrations.meta_ads.demographic_sync_service import (
    sync_all_accounts_demographics
)

logger = logging.getLogger(__name__)


def run(fecha: Optional[date] = None) -> dict:
    """
    Job que sincroniza datos demográficos de Meta Ads.
    
    Este job actualiza los registros existentes en meta_ads_anuncios_daily
    agregando información de age, gender, region, device_platform.
    
    Debe ejecutarse DESPUÉS del job meta_ads_cuentas_sync_daily.
    
    Args:
        fecha: Fecha a sincronizar (por defecto: ayer)
        
    Returns:
        Dict con resultados de la sincronización
    """
    if fecha is None:
        fecha = date.today() - timedelta(days=1)
    
    logger.info(f"🚀 Iniciando job: Meta Ads Demographics Sync - {fecha}")
    
    try:
        # Breakdowns a sincronizar (en orden de importancia)
        breakdowns = [
            'age',              # Rango de edad
            'gender',           # Género  
            'region',           # Estado/Región
            'device_platform'   # Plataforma de dispositivo
        ]
        
        result = sync_all_accounts_demographics(
            fecha=fecha,
            breakdowns=breakdowns
        )
        
        logger.info(f"✅ Job completado - {result['exitosas']}/{result['total_cuentas']} cuentas")
        
        return {
            'ok': True,
            'job': 'meta_ads_demographics_sync',
            'fecha': fecha.isoformat(),
            'resultado': result
        }
        
    except Exception as e:
        logger.error(f"❌ Error en job demographics sync: {e}", exc_info=True)
        return {
            'ok': False,
            'job': 'meta_ads_demographics_sync',
            'fecha': fecha.isoformat() if fecha else None,
            'error': str(e)
        }


if __name__ == '__main__':
    """Permite ejecutar el job manualmente"""
    import sys
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Cargar .env
    from dotenv import load_dotenv
    root_dir = Path(__file__).parent.parent.parent.parent
    load_dotenv(root_dir / '.env')
    
    # Ejecutar
    result = run()
    
    print(f"\n{'='*80}")
    print(f"RESULTADO:")
    print(f"{'='*80}")
    print(f"OK: {result['ok']}")
    print(f"Fecha: {result['fecha']}")
    
    if result['ok']:
        res = result['resultado']
        print(f"Cuentas procesadas: {res['exitosas']}/{res['total_cuentas']}")
        print(f"Errores: {res['errores']}")
        
        print(f"\nDetalle por cuenta:")
        for cuenta_result in res['resultados'][:5]:  # Primeras 5
            print(f"\n  Cuenta: {cuenta_result['account_id']}")
            for breakdown, stats in cuenta_result['breakdowns'].items():
                print(f"    {breakdown}: {stats['updated']} registros actualizados")
    else:
        print(f"Error: {result.get('error')}")
    
    print(f"{'='*80}\n")
