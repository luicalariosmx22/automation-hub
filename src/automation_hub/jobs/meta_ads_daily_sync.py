"""
Meta Ads Daily Sync Job

Sincroniza diariamente los datos de anuncios de Meta (Facebook/Instagram) desde la API
a la tabla meta_ads_anuncios_daily en Supabase.

Configuración:
- Horario: 1 AM todos los días
- Cron: 0 1 * * *
- Período: Día anterior (ayer)
"""

import os
import logging
from datetime import date, timedelta
from dotenv import load_dotenv

from automation_hub.integrations.meta_ads.daily_sync_service import MetaAdsDailySyncService

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def run():
    """
    Ejecuta la sincronización diaria de Meta Ads
    Sincroniza el día anterior para todas las cuentas activas usando la nueva tabla daily
    """
    logger.info("="*80)
    logger.info("🚀 Iniciando sincronización diaria de Meta Ads")
    logger.info("="*80)
    
    try:
        # Inicializar servicio diario
        service = MetaAdsDailySyncService()
        
        # Calcular fechas (sincronizar ayer)
        hoy = date.today()
        ayer = hoy - timedelta(days=1)
        
        logger.info(f"📅 Sincronizando datos del: {ayer}")
        
        # Ejecutar sincronización diaria
        result = service.sync_all_accounts_daily(
            fecha_reporte=ayer,
            nombre_nora=None  # Todas las cuentas
        )
        
        # Analizar resultados
        if result.get('ok'):
            logger.info("="*80)
            logger.info("✅ SINCRONIZACIÓN DIARIA COMPLETADA EXITOSAMENTE")
            logger.info("="*80)
            logger.info(f"📊 Cuentas procesadas: {result['cuentas_procesadas']}")
            logger.info(f"✅ Cuentas exitosas: {result['cuentas_exitosas']}")
            logger.info(f"❌ Cuentas con errores: {len(result['cuentas_con_errores'])}")
            
            if result['cuentas_con_errores']:
                logger.warning(f"\\n⚠️ CUENTAS CON ERRORES:")
                for error_info in result['cuentas_con_errores']:
                    logger.warning(f"  • {error_info['cuenta']} ({error_info['cuenta_id']})")
                    logger.warning(f"    Error: {error_info['error']}")
            
            logger.info("="*80)
            
            # Success pero con algunos errores
            if result['cuentas_con_errores']:
                return {
                    'success': True,
                    'message': f"Sincronización completada con {len(result['cuentas_con_errores'])} errores",
                    'stats': result
                }
            else:
                return {
                    'success': True,
                    'message': 'Sincronización completada exitosamente',
                    'stats': result
                }
        else:
            logger.error("❌ ERROR EN SINCRONIZACIÓN")
            logger.error(f"Error: {result.get('error')}")
            return {
                'success': False,
                'message': f"Error: {result.get('error')}",
                'stats': result
            }
            
    except Exception as e:
        logger.error("="*80)
        logger.error("❌ ERROR CRÍTICO EN SINCRONIZACIÓN")
        logger.error("="*80)
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f"Error crítico: {str(e)}"
        }


if __name__ == "__main__":
    # Para pruebas manuales
    result = run()
    print(f"\\nResultado: {result}")
