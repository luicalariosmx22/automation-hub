import sys
sys.path.insert(0, 'src')

from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timedelta

sb = create_client_from_env()

# Obtener fecha de hoy en México
ahora_utc = datetime.utcnow()
hoy_mexico = ahora_utc - timedelta(hours=7)
fecha_inicio = hoy_mexico.replace(hour=0, minute=0, second=0)
fecha_inicio_utc = fecha_inicio + timedelta(hours=7)

result = sb.table('meta_publicaciones_webhook').select('id, pagina_id, mensaje, imagen_url').gte('created_at', fecha_inicio_utc.isoformat()).order('created_at', desc=True).execute()

con_imagen = [p for p in result.data if p.get('imagen_url')]
sin_imagen = [p for p in result.data if not p.get('imagen_url')]

print(f"Total hoy: {len(result.data)}")
print(f"Con imagen: {len(con_imagen)}")
print(f"Sin imagen: {len(sin_imagen)}")

if con_imagen:
    print("\nPublicaciones CON imagen:")
    for p in con_imagen[:5]:
        msg = (p.get('mensaje') or '')[:40]
        print(f"  ID {p['id']}: {msg}...")
