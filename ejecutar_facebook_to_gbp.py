#!/usr/bin/env python3
"""
Ejecutar job de sincronización Facebook → GBP
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from automation_hub.jobs.meta_to_gbp_daily import run
    print("🚀 Iniciando sincronización Facebook → GBP...")
    run()
    print("✅ Sincronización completada")