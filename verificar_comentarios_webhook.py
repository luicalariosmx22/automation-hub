from dotenv import load_dotenv
import sys, os
load_dotenv()
sys.path.insert(0, 'src')

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

# Verificar comentarios en webhook
comentarios = supabase.table('meta_comentarios_webhook').select('*').order('creada_en', desc=True).limit(10).execute()

print(f"Total comentarios encontrados: {len(comentarios.data)}")

if comentarios.data:
    print("\n=== COMENTARIOS RECIENTES ===")
    for comentario in comentarios.data:
        print(f"ID: {comentario.get('comment_id')}")
        print(f"Mensaje: {comentario.get('mensaje', 'N/A')[:100]}...")
        print(f"Procesada: {comentario.get('procesada')}")
        print(f"Fecha: {comentario.get('creada_en')}")
        print("---")
else:
    print("\n❌ No hay comentarios en la tabla meta_comentarios_webhook")
    print("Esto significa que el webhook de Facebook no está enviando datos a tu base de datos.")