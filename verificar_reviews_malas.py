#!/usr/bin/env python3
"""
Script para verificar reviews malas recientes en la base de datos
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from automation_hub.db.supabase_client import get_supabase_client
    
    print("🔍 Consultando reviews malas recientes...")
    
    supabase = get_supabase_client()
    
    # Buscar reviews con 1-2 estrellas de los últimos 7 días
    reviews_malas = supabase.table("gbp_reviews").select(
        "location_name, star_rating, reviewer_display_name, comment, create_time, review_id"
    ).lte("star_rating", 2).gte(
        "create_time", "2024-12-23"  # Últimos 7 días
    ).order("create_time", desc=True).limit(10).execute()
    
    if reviews_malas.data:
        print(f"📊 Encontradas {len(reviews_malas.data)} reviews malas recientes:")
        for review in reviews_malas.data:
            location = review['location_name'].split('/')[-1] if '/' in review['location_name'] else review['location_name']
            print(f"\n🏢 Ubicación: {location}")
            print(f"⭐ Rating: {review['star_rating']} estrellas")
            print(f"👤 Autor: {review['reviewer_display_name']}")
            print(f"📅 Fecha: {review['create_time']}")
            print(f"💬 Comentario: {review['comment'][:100]}..." if len(review['comment']) > 100 else f"💬 Comentario: {review['comment']}")
            print(f"🔗 Link: https://business.google.com/reviews/l/{location}")
            print("-" * 50)
    else:
        print("✅ No se encontraron reviews malas recientes")
        
    # Mostrar estadísticas generales
    stats = supabase.table("gbp_reviews").select(
        "star_rating", count="exact"
    ).execute()
    
    if stats.data:
        total_reviews = stats.count
        malas_total = supabase.table("gbp_reviews").select(
            "review_id", count="exact"
        ).lte("star_rating", 2).execute()
        
        print(f"\n📈 Estadísticas generales:")
        print(f"📝 Total reviews: {total_reviews}")
        print(f"⚠️ Reviews malas (1-2⭐): {malas_total.count if malas_total.data else 0}")
        if total_reviews > 0:
            porcentaje = (malas_total.count / total_reviews) * 100 if malas_total.data else 0
            print(f"📊 Porcentaje de reviews malas: {porcentaje:.1f}%")