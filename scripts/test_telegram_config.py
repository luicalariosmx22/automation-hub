"""
Script para verificar y probar la configuración de notificaciones de Telegram.
"""
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.telegram_config_repo import fetch_destinatarios_telegram
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram

print("🔍 Verificando configuración de Telegram...\n")

supabase = create_client_from_env()

# Ver todos los destinatarios
print("=== Destinatarios Configurados ===")
destinatarios = fetch_destinatarios_telegram(supabase)
print(f"Total: {len(destinatarios)}\n")

for d in destinatarios:
    nombre = d.get("nombre_contacto", "Sin nombre")
    chat_id = d.get("chat_id")
    nora = d.get("nombre_nora")
    jobs = d.get("jobs_permitidos") or ["TODOS"]
    prioridades = d.get("prioridades_permitidas") or ["TODAS"]
    
    print(f"📱 {nombre}")
    print(f"   Chat ID: {chat_id}")
    print(f"   Cliente: {nora}")
    print(f"   Jobs: {', '.join(jobs)}")
    print(f"   Prioridades: {', '.join(prioridades)}")
    print()

# Probar envío
print("\n=== Probando Envío de Notificación ===")
resultado = notificar_alerta_telegram(
    nombre="🧪 Test del Sistema",
    descripcion="Sistema de notificaciones configurado correctamente",
    prioridad="media",
    datos={
        "Destinatarios": len(destinatarios),
        "Estado": "Operativo"
    },
    nombre_nora="Sistema",
    job_name="test.notifications",
    tipo_alerta="test"
)

if resultado:
    print("✅ Notificación enviada correctamente")
else:
    print("❌ Error al enviar notificación")
