"""
Job para descargar creativos de anuncios Meta Ads desde webhooks.

Descarga imágenes de creativos de anuncios de Facebook/Instagram Ads
y las almacena en Supabase Storage.

Proceso:
1. Obtiene anuncios pendientes de descargar (con creative_image pero sin creative_image_local)
2. Descarga la imagen del creativo desde la URL de Facebook
3. Sube el archivo a Supabase Storage
4. Actualiza meta_ads_anuncios_webhooks con la URL pública

Configuración:
- Procesa hasta 100 anuncios por ejecución
- Solo procesa anuncios con creative_image válido
- Manejo de idempotencia (no reprocesa archivos existentes)
"""
import logging
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.meta_ads.creative_downloader import procesar_batch, BATCH_SIZE
from automation_hub.db.repositories.alertas_repo import crear_alerta

logger = logging.getLogger(__name__)

JOB_NAME = "meta_ads_creative_download_daily"


def run(ctx=None):
    """
    Ejecuta el job de descarga de creativos de anuncios Meta Ads.
    
    Returns:
        Dict con estadísticas de ejecución
    """
    logger.info(f"🚀 Iniciando job {JOB_NAME}")
    logger.info(f"⚙️ Configuración: batch_size={BATCH_SIZE}")
    
    supabase = create_client_from_env()
    
    try:
        # Procesar batch de anuncios pendientes
        stats = procesar_batch(supabase, batch_size=BATCH_SIZE)
        
        # Resumen
        logger.info("="*80)
        logger.info("📊 RESUMEN DE EJECUCIÓN")
        logger.info(f"   Anuncios procesados: {stats['procesados']}")
        logger.info(f"   ✅ Exitosos: {stats['exitosos']}")
        logger.info(f"   ❌ Errores: {stats['errores']}")
        logger.info("="*80)
        
        # Crear alerta si hay errores significativos
        if stats['errores'] > 0 and stats['procesados'] > 0:
            tasa_error = (stats['errores'] / stats['procesados']) * 100
            if tasa_error > 20:  # Más del 20% de errores
                crear_alerta(
                    supabase=supabase,
                    nombre="Alta tasa de errores en descarga de creativos Meta Ads",
                    tipo="warning",
                    nombre_nora="sistema",
                    descripcion=f"Tasa de error: {tasa_error:.1f}% ({stats['errores']}/{stats['procesados']})",
                    evento_origen="meta_ads_creative_download_daily",
                    prioridad="media"
                )
        
        logger.info(f"✅ Job {JOB_NAME} completado exitosamente")
        
        return {
            'status': 'success',
            'procesados': stats['procesados'],
            'exitosos': stats['exitosos'],
            'errores': stats['errores']
        }
    
    except Exception as e:
        logger.error(f"❌ Error ejecutando job {JOB_NAME}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Crear alerta crítica
        try:
            crear_alerta(
                supabase=supabase,
                nombre=f"Error crítico en job {JOB_NAME}",
                tipo="error",
                nombre_nora="sistema",
                descripcion=str(e),
                evento_origen=JOB_NAME,
                prioridad="alta"
            )
        except:
            pass
        
        return {
            'status': 'error',
            'error': str(e)
        }


if __name__ == '__main__':
    # Configurar logging para ejecución standalone
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    resultado = run()
    print(f"\n{'='*80}")
    print(f"Resultado: {resultado}")
    print(f"{'='*80}")
