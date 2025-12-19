"""Cambiar el calendario seleccionado a hola@gottalent.com.mx"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

nuevo_calendar_id = "hola@gottalent.com.mx"
nombre_nora = "aura"

print(f"📅 Cambiando calendario seleccionado para {nombre_nora}")
print(f"   Nuevo calendario: {nuevo_calendar_id}")

result = supabase.table('google_calendar_sync') \
    .update({
        'google_calendar_id': nuevo_calendar_id
    }) \
    .eq('nombre_nora', nombre_nora) \
    .execute()

if result.data:
    print("\n✅ Calendario actualizado exitosamente!")
    print(f"   {result.data}")
else:
    print("\n❌ Error actualizando calendario")
    print(f"   {result}")
