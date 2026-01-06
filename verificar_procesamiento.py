#!/usr/bin/env python3
"""
Script para verificar el orden de procesamiento y últimas publicaciones procesadas
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def verificar_orden():
    """Verificar el orden de las publicaciones y cuáles se procesaron"""
    supabase = create_client_from_env()
    
    print("📊 VERIFICACIÓN DEL PROCESAMIENTO")
    print()
    
    # Últimas 10 publicaciones procesadas (publicada_gbp = true)
    procesadas = supabase.table("meta_publicaciones_webhook")\
        .select("post_id, mensaje, creada_en, publicada_gbp")\
        .eq("publicada_gbp", True)\
        .gte("creada_en", "2025-12-01")\
        .order("creada_en", desc=True)\
        .limit(10)\
        .execute()
    
    print("✅ Últimas 10 publicaciones PROCESADAS:")
    for pub in procesadas.data:
        fecha = pub.get("creada_en", "")[:16].replace("T", " ")
        mensaje = pub.get("mensaje", "")[:50] + "..." if pub.get("mensaje") else "Sin mensaje"
        print(f"   📝 {fecha} - {mensaje}")
    
    print()
    
    # Próximas 10 pendientes (publicada_gbp = false)
    pendientes = supabase.table("meta_publicaciones_webhook")\
        .select("post_id, mensaje, creada_en, publicada_gbp")\
        .eq("publicada_gbp", False)\
        .not_.is_("mensaje", "null")\
        .gte("creada_en", "2025-12-01")\
        .order("creada_en", desc=True)\
        .limit(10)\
        .execute()
    
    print("⏳ Próximas 10 publicaciones PENDIENTES:")
    for pub in pendientes.data:
        fecha = pub.get("creada_en", "")[:16].replace("T", " ")
        mensaje = pub.get("mensaje", "")[:50] + "..." if pub.get("mensaje") else "Sin mensaje"
        print(f"   ⌛ {fecha} - {mensaje}")
    
    print()
    
    # Estadísticas
    total_procesadas = supabase.table("meta_publicaciones_webhook")\
        .select("id", count="exact")\
        .eq("publicada_gbp", True)\
        .gte("creada_en", "2025-12-01")\
        .execute()
    
    total_pendientes = supabase.table("meta_publicaciones_webhook")\
        .select("id", count="exact")\
        .eq("publicada_gbp", False)\
        .not_.is_("mensaje", "null")\
        .gte("creada_en", "2025-12-01")\
        .execute()
    
    print(f"📈 ESTADÍSTICAS (dic 2025 - ene 2026):")
    print(f"   ✅ Procesadas: {total_procesadas.count}")
    print(f"   ⏳ Pendientes: {total_pendientes.count}")
    print(f"   📊 Total: {total_procesadas.count + total_pendientes.count}")
    
if __name__ == "__main__":
    verificar_orden()