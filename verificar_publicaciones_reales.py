#!/usr/bin/env python3
"""
Script para verificar cuántas publicaciones se publicaron REALMENTE en GBP vs cuántas se marcaron como procesadas por otros motivos
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def verificar_publicaciones_reales():
    """Verificar cuántas publicaciones se publicaron realmente en GBP"""
    supabase = create_client_from_env()
    
    print("🔍 ANÁLISIS DETALLADO DE PUBLICACIONES")
    print()
    
    # Publicaciones que SÍ se publicaron en GBP (tienen registro en gbp_publicaciones)
    publicadas_gbp = supabase.table("gbp_publicaciones")\
        .select("*")\
        .eq("tipo", "FROM_FACEBOOK")\
        .eq("estado", "publicado")\
        .gte("created_at", "2025-12-01")\
        .execute()
    
    print(f"✅ PUBLICADAS EXITOSAMENTE EN GBP: {len(publicadas_gbp.data)}")
    
    # Publicaciones con errores en GBP
    errores_gbp = supabase.table("gbp_publicaciones")\
        .select("*")\
        .eq("tipo", "FROM_FACEBOOK")\
        .eq("estado", "error")\
        .gte("created_at", "2025-12-01")\
        .execute()
    
    print(f"❌ CON ERRORES EN GBP: {len(errores_gbp.data)}")
    
    # Total marcadas como publicada_gbp = true
    marcadas_como_procesadas = supabase.table("meta_publicaciones_webhook")\
        .select("id", count="exact")\
        .eq("publicada_gbp", True)\
        .gte("creada_en", "2025-12-01")\
        .execute()
    
    print(f"📝 MARCADAS COMO PROCESADAS: {marcadas_como_procesadas.count}")
    
    # Las que se marcaron pero no tienen ubicaciones activas
    sin_ubicaciones = marcadas_como_procesadas.count - len(publicadas_gbp.data) - len(errores_gbp.data)
    
    print(f"🏢 SIN UBICACIONES ACTIVAS: {sin_ubicaciones}")
    
    print()
    print("📊 RESUMEN:")
    print(f"   ✅ Publicadas en GBP: {len(publicadas_gbp.data)}")
    print(f"   ❌ Errores en GBP: {len(errores_gbp.data)}")  
    print(f"   🏢 Sin ubicaciones activas: {sin_ubicaciones}")
    print(f"   📝 Total procesadas: {marcadas_como_procesadas.count}")
    
    # Mostrar algunas exitosas
    if publicadas_gbp.data:
        print()
        print("✅ Últimas 5 publicadas exitosamente en GBP:")
        for pub in publicadas_gbp.data[:5]:
            print(f"   📍 {pub.get('location_name', 'N/A')[:30]}... - {pub.get('contenido', '')[:50]}...")
    
    # Mostrar algunos errores
    if errores_gbp.data:
        print()
        print("❌ Últimos 5 errores:")
        for err in errores_gbp.data[:5]:
            error_msg = err.get('error_mensaje', '')[:80]
            print(f"   🚫 {error_msg}...")

if __name__ == "__main__":
    verificar_publicaciones_reales()