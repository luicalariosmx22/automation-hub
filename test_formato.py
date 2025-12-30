#!/usr/bin/env python3
"""
Test simple del formato de notificación
"""

# Simular datos de reviews malas
reviews_malas = [
    {
        "ubicacion": "Restaurante Centro",
        "ubicacion_nora": "Nora Centro",
        "rating": 1,
        "autor": "Ana García", 
        "texto": "Muy mala experiencia, comida fría y servicio lento",
        "fecha": "2024-12-30T10:30:00Z",
        "link_contestar": "https://business.google.com/dashboard/l/12345",
        "link_reviews": "https://business.google.com/dashboard/l/12345/reviews"
    },
    {
        "ubicacion": "Café Norte",
        "ubicacion_nora": "Nora Norte", 
        "rating": 2,
        "autor": "Carlos López",
        "texto": "No me gustó nada, muy caro para lo que ofrecen",
        "fecha": "2024-12-30T14:15:00Z",
        "link_contestar": "https://business.google.com/dashboard/l/67890",
        "link_reviews": "https://business.google.com/dashboard/l/67890/reviews"
    }
]

print("🚨 NOTIFICACIÓN DE REVIEWS MALAS")
print("=" * 50)

descripcion = f"🆕 8 reviews nuevas | 💬 2 respuestas nuevas | ⚠️ {len(reviews_malas)} reviews MALAS"
print(f"📝 Descripción: {descripcion}")
print()

print("📋 REVIEWS MALAS DETECTADAS:")
print()

for i, review in enumerate(reviews_malas):
    print(f"🏢 {review['ubicacion']} ({review['ubicacion_nora']})")
    print(f"⭐ {review['rating']} estrellas - {review['autor']}")
    print(f"💬 \"{review['texto']}\"")
    print(f"📅 {review['fecha'][:10]}")
    print(f"🔗 Dashboard: {review['link_contestar']}")
    print(f"📝 Reviews: {review['link_reviews']}")
    if i < len(reviews_malas) - 1:
        print("\n---\n")

print("\n✅ Formato de notificación verificado!")