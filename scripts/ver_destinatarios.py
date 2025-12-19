"""Ver destinatarios actuales"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.db.supabase_client import create_client_from_env

sb = create_client_from_env()
r = sb.table('notificaciones_telegram_config').select('*').execute()

print(f'\n📊 Total destinatarios: {len(r.data)}\n')

for c in r.data:
    nombre = c.get('nombre_contacto', 'Sin nombre')
    chat_id = c.get('chat_id', 'Sin chat')
    id_registro = c.get('id')
    print(f'   ID {id_registro}: {nombre} - Chat: {chat_id}')
