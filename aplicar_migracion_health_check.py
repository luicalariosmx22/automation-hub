"""
Script para aplicar la migración del job de health check en Supabase
"""
import sys
import os
from pathlib import Path

# Configurar path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Leer el archivo SQL
sql_file = project_root / "migrations" / "add_api_health_check_job.sql"

with open(sql_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Conectar a Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("❌ Error: SUPABASE_URL o SUPABASE_KEY no configurados")
    sys.exit(1)

print(f"🔗 Conectando a Supabase: {supabase_url}")
supabase = create_client(supabase_url, supabase_key)

print("\n📝 Ejecutando migración...")
print("─" * 70)

try:
    # Ejecutar el SQL
    response = supabase.rpc('exec_sql', {'sql': sql_content}).execute()
    
    print("✅ Migración aplicada exitosamente!")
    print("\n📊 Job configurado:")
    print("   Nombre: api.health_check")
    print("   Schedule: 8:00 AM y 8:00 PM todos los días")
    print("   Activo: Sí")
    print("   Servicios: 13")
    print("\n🔔 Notificaciones:")
    print("   Solo cuando algo falla (notify_on_failure: true)")
    print("   Telegram Chat: 5674082622")
    
except Exception as e:
    if "does not exist" in str(e):
        print("⚠️  La función exec_sql no existe en Supabase.")
        print("\n📋 Por favor, ejecuta manualmente en Supabase SQL Editor:")
        print("─" * 70)
        print(sql_content)
        print("─" * 70)
        print("\n💡 Ve a: https://supabase.com/dashboard/project/sylqljdiiyhtgtrghwjk/sql")
    else:
        print(f"❌ Error ejecutando migración: {e}")
        print("\n📋 SQL a ejecutar manualmente:")
        print("─" * 70)
        print(sql_content)
        print("─" * 70)
