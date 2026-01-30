"""
Test simple para verificar que los jobs funcionan.
"""
import sys
import os

# Agregar src al path para importar sin instalar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from automation_hub.jobs import api_health_check, meta_to_gbp_daily

def test_api_health():
    """Test del health check"""
    print("\n" + "="*60)
    print("TEST 1: API Health Check")
    print("="*60)
    try:
        api_health_check.run()
        print("✓ api_health_check OK")
        return True
    except Exception as e:
        print(f"✗ api_health_check FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_meta_to_gbp():
    """Test del job meta to GBP"""
    print("\n" + "="*60)
    print("TEST 2: Meta to GBP (verificando OAuth)")
    print("="*60)
    try:
        meta_to_gbp_daily.run()
        print("✓ meta_to_gbp_daily OK")
        return True
    except Exception as e:
        print(f"✗ meta_to_gbp_daily FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    results = []
    
    # Test 1
    results.append(("api_health_check", test_api_health()))
    
    # Test 2
    results.append(("meta_to_gbp_daily", test_meta_to_gbp()))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    sys.exit(0 if passed == total else 1)
