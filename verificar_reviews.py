#!/usr/bin/env python3
"""
Wrapper para ejecutar el job de reviews con detección de malas reviews
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'src')

if __name__ == "__main__":
    from automation_hub.jobs.gbp_reviews_daily import run
    print("🚀 Iniciando job de reviews con detección de malas reviews...")
    run()
    print("✅ Job completado")