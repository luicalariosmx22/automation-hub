#!/usr/bin/env python3
"""
Ejecutar el job principal con límite de videos para probar
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.jobs.meta_to_gbp_daily import run

if __name__ == "__main__":
    print("🚀 Ejecutando job meta_to_gbp_daily con límite de videos...")
    print("   📋 Máximo 10 videos por ejecución")  
    print("   ⏱️  Delay de 2 minutos entre videos")
    print("   🖼️  Sin límite para imágenes")
    print("   🔔 Notificaciones individuales habilitadas")
    print()
    
    run()