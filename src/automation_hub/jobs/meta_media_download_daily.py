"""
Job para descargar media de publicaciones Meta desde webhooks.

Descarga imágenes y videos de publicaciones de Facebook/Instagram recibidas
por webhooks y las almacena en Supabase Storage.

Proceso:
1. Obtiene publicaciones pendientes de descargar (con imagen_url pero sin imagen_local)
2. Descarga el contenido multimedia desde la URL de Facebook
3. Sube el archivo a Supabase Storage
4. Actualiza meta_publicaciones_webhook con la URL pública

Configuración:
- Procesa hasta 50 publicaciones por ejecución
- Excluye historias/stories (videos sin mensaje)
- Manejo de idempotencia (no reprocesa archivos existentes)
"""
import logging
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.meta_ads.media_downloader import procesar_batch, BATCH_SIZE
from automation_hub.db.repositories.alertas_repo import crear_alerta

logger = logging.getLogger(__name__)

JOB_NAME = "meta_media_download_daily"


def run(ctx=None):
    """
    Ejecuta el job de descarga de media desde webhooks Meta.
    
    Returns:
        Dict con estadísticas de ejecución
    """
    logger.info(f"🚀 Iniciando job {JOB_NAME}")
    logger.info(f"⚙️ Configuración: batch_size={BATCH_SIZE}")
    
    supabase = create_client_from_env()
    
    try:
        # Procesar batch de publicaciones pendientes
        stats = procesar_batch(supabase, batch_size=BATCH_SIZE)
        
        # Resumen
        logger.info("="*80)
        logger.info("📊 RESUMEN DE EJECUCIÓN")
        logger.info(f"   Publicaciones procesadas: {stats['procesadas']}")
        logger.info(f"   ✅ Exitosas: {stats['exitosas']}")
        logger.info(f"   ❌ Errores: {stats['errores']}")
        logger.info("="*80)
        
        # Crear alerta si hay errores significativos
        if stats['errores'] > 0 and stats['procesadas'] > 0:
            tasa_error = (stats['errores'] / stats['procesadas']) * 100
            if tasa_error > 20:  # Más del 20% de errores
                crear_alerta(
                    supabase=supabase,
                    tipo="warning",
                    titulo="Alta tasa de errores en descarga de media Meta",
                    mensaje=f"Tasa de error: {tasa_error:.1f}% ({stats['errores']}/{stats['procesadas']})",
                    categoria="meta_media",
                    severidad="medium"
                )
        
        logger.info(f"✅ Job {JOB_NAME} completado exitosamente")
        
        return {
            'status': 'success',
            'procesadas': stats['procesadas'],
            'exitosas': stats['exitosas'],
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
                tipo="error",
                titulo=f"Error crítico en job {JOB_NAME}",
                mensaje=str(e),
                categoria="meta_media",
                severidad="high"
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
