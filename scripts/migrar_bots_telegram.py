"""
Script para migrar bots de Telegram existentes a la base de datos.
Lee tokens del código y variables de entorno y los guarda en telegram_bots.
"""
import os
from dotenv import load_dotenv
from automation_hub.db.supabase_client import create_client_from_env

load_dotenv()

# Bots conocidos en el código
BOTS_EXISTENTES = [
    {
        "nombre": "Bot de Citas",
        "token": os.getenv("TELEGRAM_BOT_TOKEN_CITAS", "8556035050:AAF9guBOOEFnMjObUqTMpq-TtvpytUR-IZI"),
        "descripcion": "Bot para enviar resumen diario de citas de Google Calendar",
        "activo": True
    },
    {
        "nombre": "Bot Principal",
        "token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "descripcion": "Bot principal del sistema para notificaciones generales",
        "activo": True
    }
]

def migrar_bots():
    print("🤖 Migrando bots de Telegram a la base de datos...\n")
    
    supabase = create_client_from_env()
    
    for bot in BOTS_EXISTENTES:
        if not bot["token"] or bot["token"] == "":
            print(f"⏭️  Saltando {bot['nombre']} - sin token configurado")
            continue
            
        try:
            # Verificar si ya existe
            existing = supabase.table("telegram_bots").select("*").eq("token", bot["token"]).execute()
            
            if existing.data:
                print(f"✅ {bot['nombre']} - Ya existe en la base de datos")
            else:
                # Insertar
                result = supabase.table("telegram_bots").insert({
                    "nombre": bot["nombre"],
                    "token": bot["token"],
                    "descripcion": bot["descripcion"],
                    "activo": bot["activo"]
                }).execute()
                
                print(f"✅ {bot['nombre']} - Migrado exitosamente")
                print(f"   Token: {bot['token'][:15]}...{bot['token'][-10:]}")
                
        except Exception as e:
            print(f"❌ Error migrando {bot['nombre']}: {e}")
    
    # Mostrar resumen
    print("\n" + "="*60)
    all_bots = supabase.table("telegram_bots").select("*").execute()
    print(f"\n📊 Total de bots en la base de datos: {len(all_bots.data)}")
    print("\nBots configurados:")
    for bot in all_bots.data:
        status = "🟢 Activo" if bot.get("activo") else "🔴 Inactivo"
        print(f"  {status} - {bot['nombre']}")
        print(f"           Token: {bot['token'][:15]}...{bot['token'][-10:]}")
    
    print("\n✅ Migración completada!")
    print("\n💡 Ahora puedes ver y gestionar todos tus bots en:")
    print("   http://localhost:5000/telegram-system.html")

if __name__ == "__main__":
    migrar_bots()
