from automation_hub.db.supabase_client import create_client_from_env

sb = create_client_from_env()
result = sb.table('telegram_bots').select('id, nombre, activo').execute()

print('\n🤖 Bots en la base de datos:\n')
for b in result.data:
    status = '🟢 Activo' if b['activo'] else '🔴 Inactivo'
    print(f"  {b['id']}. {b['nombre']} - {status}")
