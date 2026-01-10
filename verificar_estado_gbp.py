"""
Verifica si hay publicaciones pendientes para GBP y estado de notificaciones
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def verificar_publicaciones():
    supabase = create_client_from_env()
    
    print("\n" + "="*80)
    print("VERIFICACIÓN DE PUBLICACIONES META → GBP")
    print("="*80 + "\n")
    
    # 1. Publicaciones pendientes (dic 2025/ene 2026)
    print("📋 Publicaciones pendientes para GBP (dic 2025 - ene 2026):")
    pendientes = supabase.table("meta_publicaciones_webhook")\
        .select("*")\
        .eq("publicada_gbp", False)\
        .not_.is_("mensaje", "null")\
        .gte("creada_en", "2025-12-01")\
        .order("creada_en", desc=True)\
        .limit(10)\
        .execute()
    
    print(f"   Total pendientes: {len(pendientes.data)}")
    
    if pendientes.data:
        print("\n   Últimas 5 pendientes:")
        for i, pub in enumerate(pendientes.data[:5], 1):
            print(f"   {i}. Post ID: {pub.get('post_id')}")
            print(f"      Fecha: {pub.get('creada_en')}")
            print(f"      Mensaje: {pub.get('mensaje', '')[:60]}...")
            print(f"      Imagen local: {'✅' if pub.get('imagen_local') else '❌'}")
            print(f"      Video local: {'✅' if pub.get('video_local') else '❌'}")
            print()
    
    # 2. Publicaciones ya publicadas hoy
    hoy = datetime.now().strftime('%Y-%m-%d')
    publicadas_hoy = supabase.table("gbp_publicaciones")\
        .select("*")\
        .eq("tipo", "FROM_FACEBOOK")\
        .gte("published_at", hoy)\
        .execute()
    
    print(f"\n📍 Publicaciones GBP creadas HOY ({hoy}):")
    print(f"   Total: {len(publicadas_hoy.data)}")
    
    if publicadas_hoy.data:
        print("\n   Últimas 5:")
        for i, pub in enumerate(publicadas_hoy.data[:5], 1):
            print(f"   {i}. {pub.get('nombre_nora', 'N/A')}")
            print(f"      Estado: {pub.get('estado')}")
            print(f"      Hora: {pub.get('published_at', '')[:19]}")
            print(f"      Contenido: {pub.get('contenido', '')[:60]}...")
            print()
    
    # 3. Estado del job
    print("\n⚙️  Estado del job 'meta_to_gbp_daily':")
    job_config = supabase.table("jobs_config")\
        .select("*")\
        .eq("job_name", "meta_to_gbp_daily")\
        .execute()
    
    if job_config.data:
        job = job_config.data[0]
        print(f"   Activo: {'✅' if job.get('is_active') else '❌'}")
        print(f"   Intervalo: {job.get('intervalo_minutos', 'N/A')} minutos")
        print(f"   Última ejecución: {job.get('last_run_at', 'N/A')}")
        print(f"   Próxima ejecución: {job.get('next_run_at', 'N/A')}")
    else:
        print("   ⚠️ Job no encontrado en jobs_config")
    
    # 4. Verificar páginas de Facebook configuradas
    print("\n📄 Páginas de Facebook con publicar_en_gbp=True:")
    paginas_activas = supabase.table("facebook_paginas")\
        .select("page_id, nombre, publicar_en_gbp, empresa_id")\
        .eq("publicar_en_gbp", True)\
        .execute()
    
    print(f"   Total: {len(paginas_activas.data)}")
    
    if paginas_activas.data:
        for pag in paginas_activas.data:
            print(f"   - {pag.get('nombre')}")
            print(f"     Page ID: {pag.get('page_id')}")
            print(f"     Empresa: {pag.get('empresa_id', 'Sin vincular')}")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    verificar_publicaciones()
