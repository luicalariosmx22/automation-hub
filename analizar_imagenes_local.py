import sys, os
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, 'src')

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

print("=== ANÁLISIS DE IMÁGENES EN PUBLICACIONES ===\n")

# Ver tipos de imagen_local
publicaciones = supabase.table("meta_publicaciones_webhook").select("imagen_local, imagen_url").not_.is_("imagen_local", "null").limit(20).execute()

print(f"📊 Publicaciones con imagen_local: {len(publicaciones.data)}")
print("\nEjemplos de imagen_local:")

for i, pub in enumerate(publicaciones.data[:10]):
    imagen_local = pub.get('imagen_local')
    imagen_url = pub.get('imagen_url')
    print(f"{i+1}. imagen_local: {imagen_local}")
    print(f"   imagen_url: {imagen_url}")
    print("---")

# Analizar patrones
print("\n=== ANÁLISIS DE PATRONES ===")
local_patterns = {}
for pub in publicaciones.data:
    imagen_local = pub.get('imagen_local', '')
    if imagen_local:
        if imagen_local.startswith('http://localhost'):
            local_patterns['localhost'] = local_patterns.get('localhost', 0) + 1
        elif imagen_local.startswith('http://127.0.0.1'):
            local_patterns['127.0.0.1'] = local_patterns.get('127.0.0.1', 0) + 1
        elif imagen_local.startswith('/'):
            local_patterns['path_absoluto'] = local_patterns.get('path_absoluto', 0) + 1
        elif 'app.soynoraai.com' in imagen_local:
            local_patterns['app.soynoraai.com'] = local_patterns.get('app.soynoraai.com', 0) + 1
        else:
            local_patterns['otros'] = local_patterns.get('otros', 0) + 1

print("Patrones encontrados:")
for pattern, count in local_patterns.items():
    print(f"  {pattern}: {count} imágenes")

# Ver todas las publicaciones con imagen_local
total_con_local = supabase.table("meta_publicaciones_webhook").select("count").not_.is_("imagen_local", "null").execute()
print(f"\n📈 Total publicaciones con imagen_local: {len(total_con_local.data) if total_con_local.data else 'Error obteniendo count'}")

# Ver cuántas tienen imagen_url también
con_ambas = supabase.table("meta_publicaciones_webhook").select("count").not_.is_("imagen_local", "null").not_.is_("imagen_url", "null").execute()
print(f"📈 Publicaciones con imagen_local Y imagen_url: {len(con_ambas.data) if con_ambas.data else 'Error obteniendo count'}")