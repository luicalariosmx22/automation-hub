"""Agregar Maria Jesus con su chat_id"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.automation_hub.db.repositories.telegram_config_repo import agregar_destinatario_telegram
from src.automation_hub.db.supabase_client import create_client_from_env

print("👤 Agregando Maria Jesus Camarena...\n")

sb = create_client_from_env()

# Datos de Maria Jesus
chat_id = "8334855462"  # María Martínez en Telegram
nombre = "Maria Jesus Camarena"
nombre_nora = "aura"
rol = "SUPERVISOR"

# Para SUPERVISOR: recibe alertas ALTA y MEDIA
prioridades = ["alta", "media"]

# Agregar
resultado = agregar_destinatario_telegram(
    supabase=sb,
    nombre_nora=nombre_nora,
    chat_id=chat_id,
    nombre_contacto=f"{nombre} ({rol})",
    prioridades_permitidas=prioridades,
    notas=f"Rol: {rol} - Teléfono: 5216621933798 - Email: marichuycamarena11@gmail.com"
)

if resultado:
    print(f"✅ Maria Jesus agregada exitosamente!")
    print(f"\n📋 Detalles:")
    print(f"   Nombre: {nombre}")
    print(f"   Chat ID: {chat_id}")
    print(f"   Telegram: María Martínez")
    print(f"   Rol: {rol}")
    print(f"   Notificaciones: ALTA (🚨 con sonido) + MEDIA (⚠️)")
    print(f"\n🔔 Maria Jesus recibirá alertas de:")
    print(f"   • Cuentas Meta Ads desactivadas")
    print(f"   • Anuncios rechazados")
    print(f"   • Resúmenes de métricas y reseñas")
else:
    print("❌ Error al agregar a Maria Jesus")
