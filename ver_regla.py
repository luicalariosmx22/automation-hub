import sys, os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

sys.path.insert(0, 'src')
from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()
reglas = supabase.table('meta_comentarios_reglas').select('*').eq('activa', True).execute()

if reglas.data:
    regla = reglas.data[0]
    print('=== REGLA ACTIVA ===')
    print(f'Nombre: {regla["nombre"]}')
    print(f'Página ID: {regla.get("page_id", "Cualquier página")}')
    print(f'Post ID: {regla.get("post_id", "Cualquier post")}')
    print(f'Palabras clave: {regla["palabras_clave"]}')
    print(f'Acción: {regla["accion"]}')
    print(f'Mensaje respuesta: {regla["parametros"].get("mensaje", "N/A")}')
    print('===================')
    print('')
    print('Para activar la regla, haz un comentario que contenga alguna de estas palabras:')
    for palabra in regla['palabras_clave']:
        print(f'  - "{palabra}"')
else:
    print('No hay reglas activas')