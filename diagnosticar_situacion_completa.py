#!/usr/bin/env python3
"""
Script para entender exactamente qué está pasando con las ubicaciones y publicaciones
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def diagnosticar_situacion():
    """Diagnóstico completo de la situación actual"""
    supabase = create_client_from_env()
    
    print("🔍 DIAGNÓSTICO COMPLETO DE LA SITUACIÓN")
    print("=" * 60)
    
    # 1. Ver todas las empresas con publicar_en_gbp = true
    empresas_gbp = supabase.table("facebook_paginas")\
        .select("empresa_id, page_id")\
        .eq("publicar_en_gbp", True)\
        .execute()
    
    print(f"🏢 Total empresas con publicar_en_gbp = true: {len(empresas_gbp.data)}")
    print()
    
    total_ubicaciones_activas = 0
    total_publicaciones_marcadas = 0
    total_publicaciones_exitosas = 0
    
    for empresa_data in empresas_gbp.data:
        empresa_id = empresa_data.get("empresa_id")
        page_id = empresa_data.get("page_id")
        
        print(f"🏢 EMPRESA: {empresa_id[:25]}...")
        print(f"📄 PAGE ID: {page_id}")
        
        # Ubicaciones activas
        ubicaciones_activas = supabase.table("gbp_locations")\
            .select("*")\
            .eq("empresa_id", empresa_id)\
            .eq("activa", True)\
            .execute()
        
        print(f"📍 Ubicaciones activas: {len(ubicaciones_activas.data)}")
        total_ubicaciones_activas += len(ubicaciones_activas.data)
        
        if ubicaciones_activas.data:
            for ub in ubicaciones_activas.data:
                print(f"   ✅ {ub.get('location_name', '')}")
        
        # Publicaciones marcadas como procesadas
        pub_marcadas = supabase.table("meta_publicaciones_webhook")\
            .select("id", count="exact")\
            .eq("page_id", page_id)\
            .eq("publicada_gbp", True)\
            .gte("creada_en", "2025-12-01")\
            .execute()
        
        print(f"📝 Publicaciones marcadas como procesadas: {pub_marcadas.count}")
        total_publicaciones_marcadas += pub_marcadas.count
        
        # Publicaciones exitosas en GBP
        if ubicaciones_activas.data:
            pub_exitosas = supabase.table("gbp_publicaciones")\
                .select("id", count="exact")\
                .eq("tipo", "FROM_FACEBOOK")\
                .eq("estado", "publicado")\
                .in_("location_name", [ub.get('location_name') for ub in ubicaciones_activas.data])\
                .gte("created_at", "2025-12-01")\
                .execute()
            
            print(f"✅ Publicaciones exitosas en GBP: {pub_exitosas.count}")
            total_publicaciones_exitosas += pub_exitosas.count
        else:
            print(f"✅ Publicaciones exitosas en GBP: 0 (no hay ubicaciones)")
        
        print("-" * 40)
        print()
    
    print("📊 TOTALES:")
    print(f"🏢 Empresas: {len(empresas_gbp.data)}")
    print(f"📍 Ubicaciones activas: {total_ubicaciones_activas}")
    print(f"📝 Publicaciones marcadas: {total_publicaciones_marcadas}")
    print(f"✅ Publicaciones exitosas: {total_publicaciones_exitosas}")
    print()
    
    # Ver errores recientes
    errores_recientes = supabase.table("gbp_publicaciones")\
        .select("*")\
        .eq("tipo", "FROM_FACEBOOK")\
        .eq("estado", "error")\
        .gte("created_at", "2025-12-01")\
        .order("created_at", desc=True)\
        .limit(5)\
        .execute()
    
    if errores_recientes.data:
        print("❌ Últimos 5 errores:")
        for err in errores_recientes.data:
            error_msg = err.get('error_mensaje', '')[:100]
            location = err.get('location_name', '')[:40]
            print(f"   🚫 {location} - {error_msg}...")

if __name__ == "__main__":
    diagnosticar_situacion()