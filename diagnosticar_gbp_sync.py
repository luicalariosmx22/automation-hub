import sys, os
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, 'src')

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

print("=== ANÁLISIS DE PUBLICACIONES PENDIENTES ===\n")

# 1. Ver publicaciones pendientes con mensaje
pendientes = supabase.table("meta_publicaciones_webhook").select("*").eq("publicada_gbp", False).not_.is_("mensaje", "null").execute()
print(f"📊 Publicaciones pendientes con mensaje: {len(pendientes.data)}")

if pendientes.data:
    # Agrupar por page_id para ver qué páginas tienen más publicaciones
    page_counts = {}
    for pub in pendientes.data[:10]:  # Solo primeras 10
        page_id = pub.get('page_id')
        if page_id:
            page_counts[page_id] = page_counts.get(page_id, 0) + 1
    
    print("\n📈 Publicaciones por página (primeras 10):")
    for page_id, count in page_counts.items():
        print(f"  {page_id}: {count} publicaciones")

# 2. Ver páginas de Facebook y su configuración GBP
print("\n=== CONFIGURACIÓN DE PÁGINAS FACEBOOK ===")
fb_pages = supabase.table("facebook_paginas").select("*").execute()
print(f"📄 Total páginas Facebook: {len(fb_pages.data)}")

if fb_pages.data:
    print(f"Campos disponibles: {list(fb_pages.data[0].keys())}")

gbp_enabled = [p for p in fb_pages.data if p.get('publicar_en_gbp')]
print(f"✅ Páginas con GBP habilitado: {len(gbp_enabled)}")

if gbp_enabled:
    print("\nPáginas con GBP habilitado:")
    for page in gbp_enabled[:5]:  # Primeras 5
        page_name = page.get('nombre_pagina') or page.get('name') or page.get('page_name') or 'Sin nombre'
        print(f"  {page.get('page_id')}: {page_name} (empresa: {page.get('empresa_id')})")

# 3. Ver locaciones GBP activas
print("\n=== LOCACIONES GBP ===")
gbp_locations = supabase.table("gbp_locations").select("empresa_id, location_name, nombre_nora, activa").eq("activa", True).execute()
print(f"📍 Locaciones GBP activas: {len(gbp_locations.data)}")

if gbp_locations.data:
    # Agrupar por empresa_id
    empresa_locations = {}
    for loc in gbp_locations.data:
        emp_id = loc.get('empresa_id')
        if emp_id:
            empresa_locations[emp_id] = empresa_locations.get(emp_id, 0) + 1
    
    print("\nLocaciones por empresa:")
    for emp_id, count in empresa_locations.items():
        print(f"  Empresa {emp_id}: {count} locaciones")

# 4. Identificar páginas que podrían tener problemas
print("\n=== DIAGNÓSTICO ===")

# Páginas sin empresa_id
pages_sin_empresa = [p for p in fb_pages.data if not p.get('empresa_id')]
print(f"⚠️  Páginas sin empresa_id: {len(pages_sin_empresa)}")

# Páginas con GBP habilitado pero sin locaciones
problemas = []
for page in gbp_enabled:
    empresa_id = page.get('empresa_id')
    if empresa_id:
        has_locations = any(loc.get('empresa_id') == empresa_id for loc in gbp_locations.data)
        if not has_locations:
            problemas.append(page)

print(f"❌ Páginas con GBP habilitado pero sin locaciones activas: {len(problemas)}")

if problemas:
    print("\nPáginas problemáticas:")
    for page in problemas[:3]:  # Primeras 3
        page_name = page.get('nombre_pagina') or page.get('name') or page.get('page_name') or 'Sin nombre'
        print(f"  {page.get('page_id')}: {page_name} (empresa: {page.get('empresa_id')})")

print("\n=== RECOMENDACIONES ===")
if len(gbp_enabled) == 0:
    print("🔧 ACCIÓN: Activar publicar_en_gbp=true en las páginas que quieras sincronizar")
elif len(problemas) > 0:
    print("🔧 ACCIÓN: Crear locaciones GBP para las empresas que no las tienen")
else:
    print("✅ Configuración parece correcta, el job debería funcionar")