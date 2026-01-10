"""
Verifica el estado de los anuncios en meta_ads_anuncios_webhooks
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

print("\n" + "="*80)
print("📊 DIAGNÓSTICO: meta_ads_anuncios_webhooks")
print("="*80 + "\n")

# 1. Total de anuncios
total = supabase.table('meta_ads_anuncios_webhooks').select('id', count='exact').execute()
print(f"1️⃣ Total de anuncios: {total.count}")

# 2. Anuncios con creative_image
con_creative = supabase.table('meta_ads_anuncios_webhooks') \
    .select('id', count='exact') \
    .not_.is_('creative_image', 'null') \
    .execute()
print(f"2️⃣ Anuncios con creative_image: {con_creative.count}")

# 3. Anuncios con creative_image_local
con_local = supabase.table('meta_ads_anuncios_webhooks') \
    .select('id', count='exact') \
    .not_.is_('creative_image_local', 'null') \
    .execute()
print(f"3️⃣ Anuncios con creative_image_local (ya descargados): {con_local.count}")

# 4. PENDIENTES: con creative_image pero sin creative_image_local
pendientes = supabase.table('meta_ads_anuncios_webhooks') \
    .select('id, name, creative_image, creative_image_local, status', count='exact') \
    .not_.is_('creative_image', 'null') \
    .is_('creative_image_local', 'null') \
    .execute()

print(f"4️⃣ Anuncios PENDIENTES de descargar: {pendientes.count}")

if pendientes.count > 0:
    print("\n📋 Primeros 5 anuncios pendientes:")
    for i, ad in enumerate(pendientes.data[:5], 1):
        print(f"\n   {i}. ID: {ad.get('id')}")
        print(f"      Nombre: {ad.get('name', 'N/A')[:60]}")
        print(f"      Status: {ad.get('status')}")
        print(f"      creative_image: {'✅ SÍ' if ad.get('creative_image') else '❌ NO'}")
        print(f"      creative_image_local: {'✅ YA DESCARGADO' if ad.get('creative_image_local') else '❌ PENDIENTE'}")
else:
    print("\n✅ Todos los anuncios ya tienen su creativo descargado")
    
    # Mostrar ejemplos de anuncios ya descargados
    print("\n📋 Ejemplos de anuncios CON creative_image_local:")
    ya_descargados = supabase.table('meta_ads_anuncios_webhooks') \
        .select('id, name, creative_image_local') \
        .not_.is_('creative_image_local', 'null') \
        .limit(5) \
        .execute()
    
    for i, ad in enumerate(ya_descargados.data, 1):
        print(f"\n   {i}. ID: {ad.get('id')}")
        print(f"      Nombre: {ad.get('name', 'N/A')[:60]}")
        print(f"      URL local: {ad.get('creative_image_local', '')[:80]}...")

# 5. Anuncios SIN creative_image (no hay qué descargar)
sin_creative = supabase.table('meta_ads_anuncios_webhooks') \
    .select('id', count='exact') \
    .is_('creative_image', 'null') \
    .execute()
print(f"\n5️⃣ Anuncios SIN creative_image (no hay imagen): {sin_creative.count}")

print("\n" + "="*80)
print("📊 RESUMEN:")
print(f"   • Total: {total.count}")
print(f"   • Con imagen en Facebook: {con_creative.count}")
print(f"   • Ya descargados: {con_local.count}")
print(f"   • Pendientes: {pendientes.count}")
print(f"   • Sin imagen: {sin_creative.count}")
print("="*80 + "\n")
