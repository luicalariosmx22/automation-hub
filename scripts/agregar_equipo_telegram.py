"""
Script para agregar usuarios del equipo a notificaciones de Telegram.
Instrucciones:
1. Cada usuario debe enviar un mensaje al bot: @soynoraai_alerts_bot
2. Ejecuta este script para ver los nuevos chat_ids
3. Confirma y se agregarán automáticamente
"""
import requests
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.telegram_config_repo import agregar_destinatario_telegram

# Usuarios del equipo
USUARIOS_EQUIPO = [
    {
        "nombre": "Isaias Rodriguez",
        "telefono": "5216624619198",
        "rol": "SUPERVISOR",
        "nombre_nora": "aura",
        "correo": "isaiazz1r@gmail.com"
    },
    {
        "nombre": "Maria Jesus Camarena", 
        "telefono": "5216621933798",
        "rol": "SUPERVISOR",
        "nombre_nora": "aura",
        "correo": "marichuycamarena11@gmail.com"
    },
    {
        "nombre": "Luica Larios",
        "telefono": "5216629360887", 
        "rol": "ADMIN",
        "nombre_nora": "aura",
        "correo": "hola@gottalent.com.mx"
    },
    {
        "nombre": "Raquel Arvizu",
        "telefono": "5216623675112",
        "rol": "EQUIPO",
        "nombre_nora": "aura",
        "correo": "raquelarvizu54@gmail.com"
    }
]

BOT_TOKEN = "8493648127:AAFVtFT09SYZ2W2B3dsFGkQ5X_RHVBINvDk"

print("🤖 Configurador de Equipo - Notificaciones Telegram\n")
print("=" * 60)
print("\n📋 USUARIOS A CONFIGURAR:")
for i, user in enumerate(USUARIOS_EQUIPO, 1):
    print(f"\n{i}. {user['nombre']} ({user['rol']})")
    print(f"   📧 {user['correo']}")
    print(f"   📱 {user['telefono']}")

print("\n" + "=" * 60)
print("\n⚠️  PASO 1: Cada usuario debe:")
print("   1. Abrir Telegram")
print("   2. Buscar: @soynoraai_alerts_bot")
print("   3. Enviar: /start")
print("\n🔍 PASO 2: Buscando nuevos mensajes...\n")

# Obtener updates del bot
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url, timeout=10)
data = response.json()

if not data.get("ok"):
    print(f"❌ Error: {data}")
    exit(1)

updates = data.get("result", [])
if not updates:
    print("⚠️  No hay mensajes nuevos.")
    print("👉 Pide al equipo que envíe /start al bot y vuelve a ejecutar este script.")
    exit(0)

# Mapear updates a usuarios
print("📱 Mensajes encontrados:\n")
nuevos_usuarios = []

for update in updates:
    message = update.get("message", {})
    chat = message.get("chat", {})
    
    chat_id = chat.get("id")
    first_name = chat.get("first_name", "")
    last_name = chat.get("last_name", "")
    username = chat.get("username", "")
    full_name = f"{first_name} {last_name}".strip()
    
    if not chat_id:
        continue
    
    # Buscar coincidencia con usuarios del equipo
    usuario_match = None
    for user in USUARIOS_EQUIPO:
        # Coincidencia por nombre o username
        nombre_parts = user["nombre"].lower().split()
        if any(part in full_name.lower() for part in nombre_parts):
            usuario_match = user
            break
    
    if usuario_match:
        print(f"✅ {full_name} (@{username})")
        print(f"   Chat ID: {chat_id}")
        print(f"   Rol: {usuario_match['rol']}")
        nuevos_usuarios.append({
            **usuario_match,
            "chat_id": str(chat_id),
            "telegram_name": full_name,
            "telegram_username": username
        })
    else:
        print(f"⚠️  {full_name} (@{username}) - Chat ID: {chat_id}")
        print(f"   (No coincide con usuarios del equipo)")
    
    print()

if not nuevos_usuarios:
    print("\n❌ No se encontraron coincidencias con usuarios del equipo.")
    print("👉 Verifica que los nombres en Telegram coincidan con los registrados.")
    exit(0)

print("=" * 60)
print(f"\n✅ {len(nuevos_usuarios)} usuario(s) identificado(s)")
print("\n¿Deseas agregarlos a la configuración de notificaciones? (s/n): ", end="")
respuesta = input().strip().lower()

if respuesta != 's':
    print("❌ Operación cancelada")
    exit(0)

# Agregar a la base de datos
print("\n🔧 Agregando usuarios a la configuración...\n")
supabase = create_client_from_env()

for user in nuevos_usuarios:
    try:
        # Configuración según rol
        if user["rol"] == "ADMIN":
            # Admins reciben TODO
            jobs = None  # Todos
            prioridades = None  # Todas
            notas = "Admin - Recibe todas las notificaciones"
        elif user["rol"] == "SUPERVISOR":
            # Supervisores reciben alta y media prioridad
            jobs = None  # Todos los jobs
            prioridades = ["alta", "media"]
            notas = "Supervisor - Alertas importantes"
        else:
            # Usuarios regulares y EQUIPO solo alta prioridad
            jobs = None
            prioridades = ["alta"]
            notas = "Usuario - Solo alertas críticas"
        
        config_id = agregar_destinatario_telegram(
            supabase=supabase,
            nombre_nora=user["nombre_nora"],
            chat_id=user["chat_id"],
            nombre_contacto=f"{user['nombre']} ({user['rol']})",
            jobs_permitidos=jobs,
            prioridades_permitidas=prioridades,
            notas=notas
        )
        
        print(f"✅ {user['nombre']} agregado (ID: {config_id})")
        
        # Enviar mensaje de bienvenida
        from automation_hub.integrations.telegram.notifier import TelegramNotifier
        notifier = TelegramNotifier()
        
        mensaje_bienvenida = f"""
🎉 <b>¡Bienvenido al Sistema de Alertas!</b>

Hola {user['nombre']}, has sido agregado al sistema de notificaciones automáticas.

<b>Tu configuración:</b>
• Rol: {user['rol']}
• Prioridades: {', '.join(prioridades) if prioridades else 'Todas'}
• Jobs: {'Todos' if not jobs else ', '.join(jobs)}

Recibirás notificaciones automáticas sobre:
🚨 Cuentas desactivadas
⚠️ Anuncios rechazados  
📊 Resúmenes de sincronizaciones
ℹ️ Completación de jobs

<b>Prioridades:</b>
• 🚨 Alta = Con sonido (urgente)
• ⚠️ Media = Sin sonido (importante)
• ℹ️ Baja = Sin sonido (informativo)

¡El sistema ya está enviando notificaciones!
"""
        
        notifier.enviar_mensaje(
            mensaje=mensaje_bienvenida,
            chat_id=user["chat_id"]
        )
        
    except Exception as e:
        print(f"❌ Error agregando {user['nombre']}: {e}")

print("\n" + "=" * 60)
print("✅ Configuración completada!")
print("\n📊 Resumen:")
print(f"   • Usuarios agregados: {len(nuevos_usuarios)}")
print(f"   • Sistema: Operativo")
print("\n💡 Tip: Puedes gestionar la configuración desde:")
print("   docs/GESTIONAR_NOTIFICACIONES.md")
