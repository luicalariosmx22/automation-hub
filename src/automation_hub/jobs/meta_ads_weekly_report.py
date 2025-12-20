"""
Meta Ads Weekly Report Job

Genera reportes semanales agregados de Meta Ads desde los datos detallados.
Calcula breakdowns por plataforma, insights, y métricas consolidadas.

Configuración:
- Horario: 3 AM todos los Lunes
- Cron: 0 3 * * 1
- Período: Semana anterior (lunes a domingo)
"""

import os
import logging
from datetime import date, timedelta
from dotenv import load_dotenv

from automation_hub.integrations.meta_ads import MetaAdsReportsService

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def run():
    """
    Ejecuta la generación de reportes semanales de Meta Ads
    Genera reportes de la semana anterior (lunes a domingo)
    """
    logger.info("="*80)
    logger.info("📊 Iniciando generación de reportes semanales de Meta Ads")
    logger.info("="*80)
    
    try:
        # Inicializar servicio
        service = MetaAdsReportsService()
        
        # Calcular fechas de la semana anterior
        hoy = date.today()
        
        # Calcular lunes de la semana pasada
        # weekday() devuelve 0=Lunes, 6=Domingo
        dias_desde_lunes = hoy.weekday()  # Si hoy es lunes, dias_desde_lunes = 0
        lunes_esta_semana = hoy - timedelta(days=dias_desde_lunes)
        lunes_semana_pasada = lunes_esta_semana - timedelta(days=7)
        domingo_semana_pasada = lunes_semana_pasada + timedelta(days=6)
        
        fecha_inicio = lunes_semana_pasada.isoformat()
        fecha_fin = domingo_semana_pasada.isoformat()
        
        logger.info(f"📅 Generando reportes para la semana: {fecha_inicio} → {fecha_fin}")
        
        # Ejecutar generación de reportes
        result = service.generate_weekly_reports(
            nombre_nora=None,  # Todas las cuentas
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        # Analizar resultados
        if result.get('ok'):
            logger.info("="*80)
            logger.info("✅ GENERACIÓN DE REPORTES COMPLETADA EXITOSAMENTE")
            logger.info("="*80)
            logger.info(f"📊 Cuentas procesadas: {result['cuentas_procesadas']}")
            logger.info(f"✅ Reportes exitosos: {result['reportes_exitosos']}")
            logger.info(f"💰 Gasto total: ${result['total_gasto']:.2f}")
            logger.info(f"💬 Mensajes totales: {result['total_mensajes']}")
            logger.info(f"❌ Reportes con errores: {len(result['reportes_con_errores'])}")
            
            if result['reportes_con_errores']:
                logger.warning(f"\\n⚠️ REPORTES CON ERRORES:")
                for error_info in result['reportes_con_errores']:
                    logger.warning(f"  • {error_info['cuenta']} ({error_info['cuenta_id']})")
                    logger.warning(f"    Error: {error_info['error']}")
            
            logger.info("="*80)
            
            # Success pero con algunos errores
            if result['reportes_con_errores']:
                return {
                    'success': True,
                    'message': f"Reportes generados con {len(result['reportes_con_errores'])} errores",
                    'stats': result
                }
            else:
                return {
                    'success': True,
                    'message': 'Reportes generados exitosamente',
                    'stats': result
                }
        else:
            logger.error("❌ ERROR EN GENERACIÓN DE REPORTES")
            logger.error(f"Error: {result.get('error')}")
            return {
                'success': False,
                'message': f"Error: {result.get('error')}",
                'stats': result
            }
            
    except Exception as e:
        logger.error("="*80)
        logger.error("❌ ERROR CRÍTICO EN GENERACIÓN DE REPORTES")
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
