#!/usr/bin/env python3
"""
Script para probar el job de automatización de comentarios
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from automation_hub.jobs.meta_comentarios_automation import run
    print("🤖 Iniciando job de automatización de comentarios...")
    run()
    print("✅ Job completado")