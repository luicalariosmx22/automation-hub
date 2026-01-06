#!/usr/bin/env python3
"""
Script para ejecutar el job de Meta to GBP con configuración correcta
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno desde el directorio correcto
load_dotenv()

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Importar y ejecutar el job
from automation_hub.jobs.meta_to_gbp_daily import run

if __name__ == "__main__":
    print("🚀 Ejecutando job Meta to GBP Daily con configuración corregida...")
    run()