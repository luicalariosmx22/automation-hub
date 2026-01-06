#!/usr/bin/env python3
"""
Script para resetear publicaciones marcadas como procesadas para reintento
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def resetear_publicaciones_para_reintento():
    """Resetear publicaciones que fallaron por formato incorrecto"""
    supabase = create_client_from_env()
    
    print("🔄 RESETEANDO PUBLICACIONES PARA REINTENTO")
    print("=" * 50)
    
    # Ver cuántas están marcadas como procesadas
    marcadas = supabase.table("meta_publicaciones_webhook")\
        .select("id", count="exact")\
        .eq("publicada_gbp", True)\
        .gte("creada_en", "2025-12-01")\
        .execute()
    
    print(f"📝 Publicaciones marcadas como procesadas: {marcadas.count}")
    
    # Ver cuántas realmente se publicaron exitosamente
    exitosas = supabase.table("gbp_publicaciones")\
        .select("id", count="exact")\
        .eq("tipo", "FROM_FACEBOOK")\
        .eq("estado", "publicado")\
        .gte("created_at", "2025-12-01")\
        .execute()
    
    print(f"✅ Publicaciones exitosas en GBP: {exitosas.count}")
    
    diferencia = marcadas.count - exitosas.count
    print(f"🔄 Publicaciones que necesitan reintento: {diferencia}")
    print()
    
    if diferencia > 0:
        respuesta = input("¿Resetear todas las publicaciones marcadas para reintento? (s/n): ")
        if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
            print("🔄 Reseteando publicaciones...")
            
            # Resetear todas las publicaciones marcadas como procesadas
            resultado = supabase.table("meta_publicaciones_webhook")\
                .update({"publicada_gbp": False})\
                .eq("publicada_gbp", True)\
                .gte("creada_en", "2025-12-01")\
                .execute()
            
            if resultado.data:
                print(f"✅ {len(resultado.data)} publicaciones reseteadas para reintento")
                print()
                print("🚀 AHORA PUEDES EJECUTAR EL JOB NUEVAMENTE:")
                print("   python -m automation_hub.jobs.meta_to_gbp_daily")
            else:
                print("❌ Error al resetear publicaciones")
        else:
            print("❌ Operación cancelada")
    else:
        print("✅ No hay publicaciones que necesiten reintento")

if __name__ == "__main__":
    resetear_publicaciones_para_reintento()