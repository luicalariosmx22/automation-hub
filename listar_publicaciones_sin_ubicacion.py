#!/usr/bin/env python3
"""
Script para listar publicaciones que necesitan ubicaciones GBP activas
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def listar_publicaciones_sin_ubicacion():
    """Lista publicaciones que necesitan ubicaciones GBP activas"""
    supabase = create_client_from_env()
    
    print("📋 PUBLICACIONES QUE NECESITAN UBICACIONES GBP ACTIVAS")
    print("=" * 60)
    
    # Obtener empresas que quieren publicar en GBP
    empresas_gbp = supabase.table("facebook_paginas")\
        .select("empresa_id, page_id, publicar_en_gbp")\
        .eq("publicar_en_gbp", True)\
        .execute()
    
    print(f"🏢 Empresas con publicar_en_gbp = True: {len(empresas_gbp.data)}")
    print()
    
    for empresa_data in empresas_gbp.data:
        empresa_id = empresa_data.get("empresa_id")
        page_id = empresa_data.get("page_id")
        
        # Verificar si tiene ubicaciones activas
        ubicaciones_activas = supabase.table("gbp_locations")\
            .select("*")\
            .eq("empresa_id", empresa_id)\
            .eq("activa", True)\
            .execute()
        
        # Si no tiene ubicaciones activas, mostrar sus publicaciones que se marcaron como procesadas pero no se publicaron
        if not ubicaciones_activas.data:
            # Obtener publicaciones que se "procesaron" pero no tienen registro exitoso en GBP
            publicaciones_marcadas = supabase.table("meta_publicaciones_webhook")\
                .select("*")\
                .eq("page_id", page_id)\
                .eq("publicada_gbp", True)\
                .not_.is_("mensaje", "null")\
                .gte("creada_en", "2025-12-01")\
                .order("creada_en", desc=True)\
                .limit(5)\
                .execute()
            
            if publicaciones_marcadas.data:
                print(f"🏢 EMPRESA: {empresa_id}")
                print(f"📄 Page ID: {page_id}")
                print(f"📊 Publicaciones marcadas pero NO publicadas: {len(publicaciones_marcadas.data)}+ (mostrando 5)")
                
                # Mostrar ubicaciones inactivas disponibles
                ubicaciones_inactivas = supabase.table("gbp_locations")\
                    .select("*")\
                    .eq("empresa_id", empresa_id)\
                    .eq("activa", False)\
                    .execute()
                
                if ubicaciones_inactivas.data:
                    print(f"📍 Ubicaciones INACTIVAS disponibles:")
                    for ub in ubicaciones_inactivas.data:
                        location_name = ub.get("location_name", "")
                        print(f"   🔸 {location_name}")
                else:
                    print(f"❌ No hay ubicaciones (ni activas ni inactivas) para esta empresa")
                
                print(f"📝 Ejemplos de publicaciones:")
                for i, pub in enumerate(publicaciones_marcadas.data, 1):
                    fecha = pub.get("creada_en", "")[:16].replace("T", " ")
                    mensaje = pub.get("mensaje", "")[:80] + "..." if len(pub.get("mensaje", "")) > 80 else pub.get("mensaje", "")
                    print(f"   {i}. {fecha} - {mensaje}")
                
                print()
                print("🛠️ Para activar una ubicación:")
                print(f"   UPDATE gbp_locations SET activa = true WHERE empresa_id = '{empresa_id}' AND location_name = 'UBICACION_A_ELEGIR';")
                print()
                print("-" * 60)
                print()
    
    # Resumen final
    print("📊 RESUMEN:")
    total_empresas_sin_ubicaciones = 0
    total_publicaciones_bloqueadas = 0
    
    for empresa_data in empresas_gbp.data:
        empresa_id = empresa_data.get("empresa_id")
        page_id = empresa_data.get("page_id")
        
        ubicaciones_activas = supabase.table("gbp_locations")\
            .select("id", count="exact")\
            .eq("empresa_id", empresa_id)\
            .eq("activa", True)\
            .execute()
        
        if ubicaciones_activas.count == 0:
            total_empresas_sin_ubicaciones += 1
            
            # Contar todas las publicaciones marcadas como procesadas pero sin ubicaciones
            pub_count = supabase.table("meta_publicaciones_webhook")\
                .select("id", count="exact")\
                .eq("page_id", page_id)\
                .eq("publicada_gbp", True)\
                .not_.is_("mensaje", "null")\
                .gte("creada_en", "2025-12-01")\
                .execute()
            
            total_publicaciones_bloqueadas += pub_count.count
    
    print(f"🏢 Empresas sin ubicaciones activas: {total_empresas_sin_ubicaciones}")
    print(f"📝 Total publicaciones bloqueadas: {total_publicaciones_bloqueadas}")

if __name__ == "__main__":
    listar_publicaciones_sin_ubicacion()