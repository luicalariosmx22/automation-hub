"""
Script para agregar a Maria Jesus al sistema de notificaciones.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.db.repositories.telegram_config_repo import agregar_destinatario_telegram
from src.automation_hub.db.supabase_client import create_client_from_env

print("👤 Agregando a Maria Jesus...\n")

# Datos de Maria Jesus
datos = {
    "nombre": "Maria Jesus Camarena",
    "correo": "marichuycamarena11@gmail.com", 
    "telefono": "5216621933798",
    "rol": "SUPERVISOR",
    "nombre_nora": "aura"
}

# Primero verificar si ya existe
supabase = create_client_from_env()
result = supabase.table("notificaciones_telegram_config").select("*").execute()

print(f"📊 Destinatarios actuales: {len(result.data)}\n")
for config in result.data:
    nombre = config.get("nombre_contacto", "Sin nombre")
    chat_id = config.get("chat_id", "Sin chat_id")
    print(f"   • {nombre} - Chat ID: {chat_id}")

# Verificar si Maria Jesus ya existe
existe = False
for config in result.data:
    if config.get("nombre_contacto") == datos["nombre"]:
        print(f"\n⚠️ Maria Jesus ya existe con chat_id: {config.get('chat_id')}")
        existe = True
        break

if not existe:
    print(f"\n❌ Maria Jesus NO está en el sistema")
    print("\n💡 Para agregarla necesitas:")
    print("   1. Que ella inicie chat con @soynoraai_alerts_bot")
    print("   2. Ejecutar: python scripts/setup_telegram_bot.py")
    print("   3. Obtener su chat_id")
    print("   4. Luego ejecutar este script con su chat_id\n")
    
    # Preguntar si tiene el chat_id
    chat_id_input = input("¿Tienes su chat_id? (déjalo vacío si no): ").strip()
    
    if chat_id_input:
        try:
            chat_id = int(chat_id_input)
            
            # Agregar a Maria Jesus
            resultado = agregar_destinatario_telegram(
                nombre_nora=datos["nombre_nora"],
                chat_id=chat_id,
                nombre_contacto=datos["nombre"],
                correo=datos["correo"],
                telefono=datos["telefono"],
                rol=datos["rol"]
            )
            
            if resultado:
                print(f"\n✅ Maria Jesus agregada exitosamente!")
                print(f"   Chat ID: {chat_id}")
                print(f"   Rol: {datos['rol']} (recibe alertas ALTA y MEDIA)")
            else:
                print("\n❌ Error al agregar a Maria Jesus")
        except ValueError:
            print("\n❌ Chat ID inválido")
    else:
        print("\n⏭️ Omitiendo agregado - obtén primero su chat_id")
else:
    print("\n✅ Maria Jesus ya está configurada")
