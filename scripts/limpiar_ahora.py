"""Limpiar duplicados y agregar Maria Jesus"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.db.supabase_client import create_client_from_env
from collections import defaultdict

print("🧹 Limpiando duplicados...\n")

sb = create_client_from_env()

# Obtener todos los destinatarios
r = sb.table('notificaciones_telegram_config').select('*').execute()
print(f"📊 Registros actuales: {len(r.data)}\n")

# Agrupar por chat_id
por_chat = defaultdict(list)
for config in r.data:
    chat_id = config.get('chat_id')
    if chat_id:
        por_chat[chat_id].append(config)

# Eliminar duplicados (mantener el más antiguo)
eliminados = 0
for chat_id, configs in por_chat.items():
    if len(configs) > 1:
        nombre = configs[0].get('nombre_contacto', 'Desconocido')
        print(f"🔄 {nombre} (Chat {chat_id}): {len(configs)} registros")
        
        # Ordenar por ID y mantener el primero
        configs_ordenados = sorted(configs, key=lambda x: x.get('id', 0))
        mantener = configs_ordenados[0]
        eliminar = configs_ordenados[1:]
        
        print(f"   ✅ Mantener ID: {mantener.get('id')}")
        print(f"   ❌ Eliminar IDs: {[c.get('id') for c in eliminar]}")
        
        # Eliminar duplicados
        for config in eliminar:
            sb.table('notificaciones_telegram_config').delete().eq('id', config.get('id')).execute()
            eliminados += 1
        print()

print(f"\n✅ Duplicados eliminados: {eliminados}\n")

# Verificar estado final
r_final = sb.table('notificaciones_telegram_config').select('*').execute()
print(f"📊 Registros finales: {len(r_final.data)}\n")
for c in r_final.data:
    nombre = c.get('nombre_contacto', 'Sin nombre')
    chat_id = c.get('chat_id')
    print(f"   • {nombre} - Chat: {chat_id}")
