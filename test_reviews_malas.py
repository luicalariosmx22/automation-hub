#!/usr/bin/env python3
"""
Test del nuevo sistema de detección de reviews malas con datos simulados
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Configurar PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from automation_hub.integrations.telegram.notifier import TelegramNotifier
    
    print("🧪 Simulando notificación de reviews malas...")
    
    # Datos simulados de reviews malas
    reviews_malas_simuladas = [
        {
            "ubicacion": "Sucursal Centro",
            "ubicacion_nora": "Nora Centro",
            "rating": 1,
            "autor": "Cliente Molesto",
            "texto": "Pésimo servicio, muy lenta la atención y el personal es grosero. No recomiendo para nada este lugar.",
            "fecha": datetime.now().isoformat(),
            "review_id": "sim123",
            "location_api_path": "accounts/108588765717064365703/locations/10476567461822527708",
            "link_contestar": "https://business.google.com/reviews/l/10476567461822527708"
        },
        {
            "ubicacion": "Sucursal Norte",
            "ubicacion_nora": "Nora Norte",
            "rating": 2,
            "autor": "María González",
            "texto": "La comida estaba fría y tardaron mucho en atenderme. Esperaba mucho más.",
            "fecha": datetime.now().isoformat(),
            "review_id": "sim456",
            "location_api_path": "accounts/108588765717064365703/locations/5678901234567890123",
            "link_contestar": "https://business.google.com/reviews/l/5678901234567890123"
        }
    ]
    
    # Construir datos para Telegram como lo haría el job real
    datos_telegram = {
        "Reviews Nuevas": 12,
        "Respuestas Nuevas": 3,
        "⚠️ REVIEWS MALAS": len(reviews_malas_simuladas),
        "Locaciones Procesadas": 25,
        "🚨 Malas en": "Centro (1), Norte (1)"
    }
    
    # Construir mensaje detallado
    mensaje_reviews_malas = "📋 REVIEWS MALAS DETECTADAS:\n\n"
    for i, review in enumerate(reviews_malas_simuladas):
        mensaje_reviews_malas += f"🏢 {review['ubicacion']} ({review['ubicacion_nora']})\n"
        mensaje_reviews_malas += f"⭐ {review['rating']} estrellas - {review['autor']}\n"
        mensaje_reviews_malas += f"💬 \"{review['texto']}\"\n"
        mensaje_reviews_malas += f"🔗 Contestar: {review['link_contestar']}\n"
        if i < len(reviews_malas_simuladas) - 1:
            mensaje_reviews_malas += "\n---\n\n"
    
    datos_telegram["Detalle Reviews Malas"] = mensaje_reviews_malas
    
    # Enviar notificación de prueba
    bot_token = "8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE"
    chat_id = "5674082622"
    notifier = TelegramNotifier(bot_token=bot_token, default_chat_id=chat_id)
    
    descripcion = f"🆕 12 reviews nuevas | 💬 3 respuestas nuevas | ⚠️ {len(reviews_malas_simuladas)} reviews MALAS"
    
    print(f"📱 Enviando notificación con descripción: {descripcion}")
    print(f"📋 Detalles de reviews malas:")
    for review in reviews_malas_simuladas:
        print(f"  - {review['ubicacion']}: {review['rating']}⭐ por {review['autor']}")
        print(f"    Link: {review['link_contestar']}")
    
    try:
        notifier.enviar_alerta(
            nombre="🚨 Reviews GBP Sincronizadas",
            descripcion=descripcion,
            prioridad="alta",
            datos=datos_telegram
        )
        print("✅ Notificación enviada exitosamente!")
    except Exception as e:
        print(f"❌ Error enviando notificación: {e}")