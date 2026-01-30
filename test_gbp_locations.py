"""
Script de prueba para el job gbp_locations_sync
"""
import sys
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Ejecutar el job
from automation_hub.jobs import gbp_locations_sync

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING: gbp_locations_sync")
    print("=" * 60)
    
    try:
        gbp_locations_sync.run()
        print("\n✓ TEST PASSED")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
