#!/usr/bin/env python3
"""
Diagnóstico rápido de entorno
"""
import os
from dotenv import load_dotenv

def diagnosticar():
    print("🔍 DIAGNÓSTICO DE ENTORNO")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Buscar archivo .env
    env_files = [".env", ".env.local", ".env.production"]
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"✅ Encontrado: {env_file}")
            load_dotenv(env_file)
        else:
            print(f"❌ No existe: {env_file}")
    
    # Verificar variables
    vars_needed = ["SUPABASE_URL", "SUPABASE_KEY", "GOOGLE_CLIENT_ID"]
    for var in vars_needed:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:10]}..." if len(value) > 10 else f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NO CONFIGURADO")
    
    print(f"\n🎯 POST A PROBAR: 244796979033974_1294237509401540")
    
if __name__ == "__main__":
    diagnosticar()