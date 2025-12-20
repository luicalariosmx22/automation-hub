"""
Script para probar el resumen diario de citas con el bot específico
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / 'src'))

from automation_hub.jobs import calendar_daily_summary

if __name__ == "__main__":
    print("Ejecutando resumen diario de citas...")
    print("="*80)
    
    try:
        calendar_daily_summary.run()
        print("\n" + "="*80)
        print("✅ Resumen de citas ejecutado exitosamente")
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ Error: {e}")
