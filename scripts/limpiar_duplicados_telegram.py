"""
Script para limpiar destinatarios duplicados de Telegram.
"""
from automation_hub.db.supabase_client import create_client_from_env
from collections import defaultdict
from typing import List, Dict, Any, cast

print("🧹 Limpiando destinatarios duplicados...\n")

supabase = create_client_from_env()

# Obtener todos los destinatarios
result = supabase.table("notificaciones_telegram_config").select("*").execute()

if not result.data:
    print("No hay destinatarios configurados")
    exit(0)

configs = cast(List[Dict[str, Any]], result.data)

# Agrupar por chat_id
por_chat_id = defaultdict(list)
for config in configs:
    chat_id = config.get("chat_id")
    if chat_id:
        por_chat_id[chat_id].append(config)

print("📊 Análisis de duplicados:\n")
total_duplicados = 0

for chat_id, config_list in por_chat_id.items():
    if len(config_list) > 1:
        nombre = config_list[0].get("nombre_contacto", "Desconocido")
        print(f"❌ {nombre} (Chat ID: {chat_id})")
        print(f"   Duplicados: {len(config_list)} registros")
        total_duplicados += len(config_list) - 1
        
        # Mostrar IDs
        ids = [str(c.get("id")) for c in config_list]
        print(f"   IDs: {', '.join(ids)}")
        print()

if total_duplicados == 0:
    print("✅ No hay duplicados")
    exit(0)

print(f"Total duplicados a eliminar: {total_duplicados}\n")
print("¿Deseas eliminar los duplicados? (s/n): ", end="")
respuesta = input().strip().lower()

if respuesta != 's':
    print("❌ Operación cancelada")
    exit(0)

print("\n🗑️  Eliminando duplicados...\n")

eliminados = 0
for chat_id, configs in por_chat_id.items():
    if len(configs) > 1:
        # Mantener el primero (más antiguo), eliminar el resto
        configs_sorted = sorted(configs, key=lambda x: x.get("created_at", ""))
        mantener = configs_sorted[0]
        eliminar = configs_sorted[1:]
        
        nombre = mantener.get("nombre_contacto", "Desconocido")
        print(f"  Procesando: {nombre}")
        print(f"  ✅ Manteniendo ID: {mantener['id']}")
        
        for config in eliminar:
            try:
                supabase.table("notificaciones_telegram_config")\
                    .delete()\
                    .eq("id", config["id"])\
                    .execute()
                print(f"  🗑️  Eliminado ID: {config['id']}")
                eliminados += 1
            except Exception as e:
                print(f"  ❌ Error eliminando ID {config['id']}: {e}")
        
        print()

print("=" * 60)
print(f"✅ Limpieza completada!")
print(f"   Duplicados eliminados: {eliminados}")
print(f"\n📊 Resumen final:")

# Mostrar configuración final
result_final = supabase.table("notificaciones_telegram_config").select("*").eq("activo", True).execute()
configs_final = cast(List[Dict[str, Any]], result_final.data)
print(f"   Total destinatarios activos: {len(configs_final)}")
for config in configs_final:
    nombre = config.get("nombre_contacto", "Sin nombre")
    chat_id = config.get("chat_id")
    print(f"   • {nombre} - Chat ID: {chat_id}")

