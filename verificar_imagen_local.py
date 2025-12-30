from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timedelta

sb = create_client_from_env()

# Publicaciones de hoy con imagen
hoy_utc = datetime.utcnow().replace(hour=0, minute=0, second=0)
result = sb.table('meta_publicaciones_webhook').select(
    'id, page_id, imagen_url, imagen_local, imagen_descargada_en'
).gte('creada_en', hoy_utc.isoformat()).execute()

print(f"\n📊 VERIFICACIÓN DE IMÁGENES:\n")
print("=" * 100)

for pub in result.data:
    tiene_url = bool(pub.get('imagen_url'))
    tiene_local = bool(pub.get('imagen_local'))
    
    print(f"\n🆔 ID: {pub['id']}")
    print(f"   imagen_url: {'✅ SÍ' if tiene_url else '❌ NO'}")
    if tiene_url:
        print(f"   URL: {pub['imagen_url'][:80]}...")
    print(f"   imagen_local: {'✅ SÍ' if tiene_local else '❌ NO'}")
    if tiene_local:
        print(f"   Local: {pub['imagen_local'][:80]}...")
    print(f"   Descargada: {pub.get('imagen_descargada_en') or 'NUNCA'}")

con_local = len([p for p in result.data if p.get('imagen_local')])
con_url = len([p for p in result.data if p.get('imagen_url')])

print("\n" + "=" * 100)
print(f"\n📈 RESUMEN:")
print(f"   Total publicaciones: {len(result.data)}")
print(f"   Con imagen_url: {con_url}")
print(f"   Con imagen_local: {con_local}")
print(f"   Faltantes por descargar: {con_url - con_local}\n")
