from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime

supabase = create_client_from_env()

# Publicaciones de hoy con mensaje NO vacío
hoy = datetime.utcnow().date()
response = supabase.table('meta_publicaciones_webhook').select('id, page_id, mensaje, tipo_item, imagen_url, imagen_local').gte('creada_en', str(hoy)).order('creada_en', desc=True).execute()

con_mensaje = [p for p in response.data if p.get('mensaje') and p['mensaje'].strip()]
sin_mensaje = [p for p in response.data if not p.get('mensaje') or not p['mensaje'].strip()]

print(f'\n=== PUBLICACIONES DE HOY ===')
print(f'Total: {len(response.data)}')
print(f'Con mensaje: {len(con_mensaje)}')
print(f'Sin mensaje: {len(sin_mensaje)}')

if con_mensaje:
    print(f'\n=== CON MENSAJE ({len(con_mensaje)}) ===')
    for p in con_mensaje[:10]:
        msg_preview = p['mensaje'][:80] + '...' if len(p['mensaje']) > 80 else p['mensaje']
        print(f"\nID {p['id']}: {p['tipo_item']}")
        print(f"  Mensaje: {msg_preview}")
        print(f"  Imagen URL: {'✅' if p.get('imagen_url') else '❌'}")
        print(f"  Imagen Local: {'✅' if p.get('imagen_local') else '❌'}")
else:
    print('\n❌ NO HAY PUBLICACIONES CON MENSAJE HOY')
    print('\nEjemplo de publicación sin mensaje:')
    if sin_mensaje:
        p = sin_mensaje[0]
        print(f"  ID {p['id']}: {p['tipo_item']}")
        print(f"  Mensaje: '{p.get('mensaje')}'")
