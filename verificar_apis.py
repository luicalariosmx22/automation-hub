"""
Script para ejecutar manualmente la verificación de APIs/Tokens.

Uso:
    python verificar_apis.py
"""
import sys
import os
import logging
from pathlib import Path

# Configurar path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Cargar .env
from dotenv import load_dotenv
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Ejecuta la verificación de APIs."""
    try:
        # Importar después de configurar el path
        from automation_hub.jobs.api_health_check import run
        
        logger.info("="*70)
        logger.info("🔍 Iniciando verificación de APIs y Tokens...")
        logger.info("="*70)
        
        resultado = run()
        
        logger.info("="*70)
        logger.info("📊 RESUMEN")
        logger.info("="*70)
        logger.info(f"Total servicios: {resultado['total_servicios']}")
        logger.info(f"✅ Funcionando: {resultado['servicios_ok']}")
        logger.info(f"❌ Con problemas: {resultado['servicios_fallando']}")
        
        if resultado['servicios_fallando'] > 0:
            logger.warning(f"\n⚠️ Servicios con problemas:")
            for servicio in resultado['servicios_con_error']:
                error = resultado['resultados'][servicio]['mensaje']
                logger.warning(f"  • {servicio}: {error}")
        else:
            logger.info("\n✅ ¡Todos los servicios funcionando correctamente!")
        
        logger.info("="*70)
        
        return 0 if resultado['servicios_fallando'] == 0 else 1
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando verificación: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
