from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timedelta

sb = create_client_from_env()

# Obtener fecha de hoy en México (UTC-7)
ahora_utc = datetime.utcnow()
hoy_mexico = ahora_utc - timedelta(hours=7)
fecha_inicio = hoy_mexico.replace(hour=0, minute=0, second=0, microsecond=0)
fecha_fin = hoy_mexico.replace(hour=23, minute=59, second=59, microsecond=999999)

# Convertir a UTC para la consulta
fecha_inicio_utc = fecha_inicio + timedelta(hours=7)
fecha_fin_utc = fecha_fin + timedelta(hours=7)

print(f"\n📅 Buscando publicaciones del {hoy_mexico.strftime('%Y-%m-%d')} (hoy en México)\n")

result = sb.table('meta_publicaciones_webhook').select(
    'id, pagina_id, mensaje, imagen_url, created_at'
).gte('created_at', fecha_inicio_utc.isoformat()).lte('created_at', fecha_fin_utc.isoformat()).order('created_at', desc=True).execute()

publicaciones = result.data

print(f"Total publicaciones hoy: {len(publicaciones)}\n")

con_imagen = 0
sin_imagen = 0

for pub in publicaciones:
    tiene_imagen = pub.get('imagen_url') and pub['imagen_url'] != ''
    emoji = "🖼️" if tiene_imagen else "📝"
    
    if tiene_imagen:
        con_imagen += 1
    else:
        sin_imagen += 1
    
    mensaje_preview = pub.get('mensaje', '')[:50] + '...' if pub.get('mensaje') and len(pub.get('mensaje', '')) > 50 else pub.get('mensaje', '')
    
    print(f"{emoji} ID {pub['id']} - Página {pub['pagina_id']}")
    print(f"   Mensaje: {mensaje_preview}")
    if tiene_imagen:
        print(f"   📷 Imagen: {pub['imagen_url'][:80]}...")
    print()

print(f"\n📊 Resumen:")
print(f"   🖼️  Con imagen: {con_imagen}")
print(f"   📝 Sin imagen: {sin_imagen}")
