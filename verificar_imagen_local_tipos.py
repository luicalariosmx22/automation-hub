import sys, os
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, 'src')
from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()
pubs = supabase.table('meta_publicaciones_webhook').select('imagen_local').not_.is_('imagen_local', 'null').limit(5).execute()

print('=== EJEMPLOS DE imagen_local REALES ===')
for i, pub in enumerate(pubs.data):
    imagen_local = pub.get('imagen_local')
    print(f'{i+1}. {imagen_local}')
    
    # Detectar tipo
    if 'supabase.co/storage/v1/object/public' in imagen_local:
        print('   -> Supabase Storage (público)')
    elif 'app.soynoraai.com' in imagen_local:
        print('   -> App SoyNoraAI')
    else:
        print('   -> Otro tipo')
    print()