"""Ejecutar health check para verificar todas las APIs"""
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print("=" * 80)
print("🔍 EJECUTANDO: Health Check de APIs/Tokens")
print("=" * 80)
print()

from automation_hub.jobs import api_health_check

try:
    resultado = api_health_check.run()
    
    print("\n" + "=" * 80)
    print(f"📊 Resultado: {resultado['servicios_ok']}/{resultado['total_servicios']} servicios OK")
    
    if resultado['servicios_fallando'] > 0:
        print(f"\n⚠️ Servicios con problemas:")
        for servicio in resultado['servicios_con_error']:
            print(f"  ❌ {servicio}")
    else:
        print("\n✅ Todos los servicios funcionando correctamente")
    
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ Error en health check: {e}")
    import traceback
    traceback.print_exc()
