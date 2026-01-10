"""
Script para probar el job de descarga de media Meta.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from automation_hub.jobs.meta_media_download_daily import run

if __name__ == '__main__':
    # Configurar logging detallado
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*80)
    print("🧪 PROBANDO JOB: meta_media_download_daily")
    print("="*80 + "\n")
    
    try:
        resultado = run()
        
        print("\n" + "="*80)
        print("📊 RESULTADO:")
        print(f"   Estado: {resultado.get('status')}")
        print(f"   Procesadas: {resultado.get('procesadas', 0)}")
        print(f"   Exitosas: {resultado.get('exitosas', 0)}")
        print(f"   Errores: {resultado.get('errores', 0)}")
        
        if resultado.get('error'):
            print(f"   Error: {resultado.get('error')}")
        
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error ejecutando job: {e}")
        import traceback
        traceback.print_exc()
