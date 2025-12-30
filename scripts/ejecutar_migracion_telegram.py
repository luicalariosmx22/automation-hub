"""
Script para ejecutar la migración del sistema de Telegram.
"""
import os
from dotenv import load_dotenv
from automation_hub.db.supabase_client import create_client_from_env

load_dotenv()

def ejecutar_migracion():
    print("📊 Ejecutando migración del sistema de Telegram...")
    
    # Leer el archivo SQL
    sql_path = "db/migrations/006_telegram_system.sql"
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Conectar a Supabase
    supabase = create_client_from_env()
    
    # Ejecutar la migración
    try:
        # Nota: Supabase no ejecuta SQL directamente desde Python
        # Necesitas ejecutar esto manualmente en el SQL Editor de Supabase
        print("\n⚠️  IMPORTANTE:")
        print("Debes ejecutar este SQL manualmente en el SQL Editor de Supabase:")
        print("\n" + "="*60)
        print(sql)
        print("="*60)
        print("\n📌 Pasos:")
        print("1. Ve a https://supabase.com/dashboard")
        print("2. Selecciona tu proyecto")
        print("3. Ve a 'SQL Editor'")
        print("4. Copia y pega el SQL de arriba")
        print("5. Click en 'Run'")
        print("\n✅ Una vez ejecutado, el sistema de Telegram estará listo!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    ejecutar_migracion()
