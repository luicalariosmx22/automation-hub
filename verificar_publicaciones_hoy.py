"""
Verifica publicaciones de HOY - Meta y GBP
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def verificar_hoy():
    supabase = create_client_from_env()
    
    hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    hoy_str = hoy_inicio.strftime('%Y-%m-%d')
    
    print("\n" + "="*80)
    print(f"📅 PUBLICACIONES DEL DÍA: {hoy_str}")
    print("="*80 + "\n")
    
    # 1. Publicaciones de Facebook recibidas HOY
    print("📱 Publicaciones de Facebook recibidas HOY:")
    pubs_facebook_hoy = supabase.table("meta_publicaciones_webhook")\
        .select("*")\
        .gte("creada_en", hoy_str)\
        .order("creada_en", desc=True)\
        .execute()
    
    print(f"   Total recibidas hoy: {len(pubs_facebook_hoy.data)}\n")
    
    if pubs_facebook_hoy.data:
        print("   Detalles:")
        for i, pub in enumerate(pubs_facebook_hoy.data, 1):
            print(f"\n   {i}. Post ID: {pub.get('post_id')}")
            print(f"      Hora: {pub.get('creada_en', '')[:19]}")
            print(f"      Mensaje: {pub.get('mensaje', 'Sin mensaje')[:80]}...")
            print(f"      Imagen local: {'✅ ' + pub.get('imagen_local', '')[:50] if pub.get('imagen_local') else '❌ No'}")
            print(f"      Video local: {'✅ ' + pub.get('video_local', '')[:50] if pub.get('video_local') else '❌ No'}")
            print(f"      Publicada en GBP: {'✅ Sí' if pub.get('publicada_gbp') else '❌ No (pendiente)'}")
            
            # Verificar si tiene URL válida de Supabase
            tiene_supabase = False
            for campo in ['imagen_local', 'video_local', 'imagen_url']:
                url = pub.get(campo, '')
                if url and 'supabase' in url.lower() and 'storage' in url.lower():
                    tiene_supabase = True
                    break
            
            print(f"      URL Supabase válida: {'✅ Sí' if tiene_supabase else '⚠️  No - NO se publicará'}")
    else:
        print("   ⚠️  No hay publicaciones de Facebook recibidas hoy")
    
    # 2. Publicaciones YA PUBLICADAS en GBP hoy
    print(f"\n{'='*80}")
    print("📍 Publicaciones YA PUBLICADAS en GBP HOY:")
    pubs_gbp_hoy = supabase.table("gbp_publicaciones")\
        .select("*")\
        .eq("tipo", "FROM_FACEBOOK")\
        .gte("published_at", hoy_str)\
        .order("published_at", desc=True)\
        .execute()
    
    print(f"   Total publicadas en GBP hoy: {len(pubs_gbp_hoy.data)}\n")
    
    if pubs_gbp_hoy.data:
        print("   Detalles:")
        exitosas = [p for p in pubs_gbp_hoy.data if p.get('estado') == 'publicada']
        errores = [p for p in pubs_gbp_hoy.data if p.get('estado') == 'error']
        
        print(f"   ✅ Exitosas: {len(exitosas)}")
        print(f"   ❌ Errores: {len(errores)}\n")
        
        for i, pub in enumerate(pubs_gbp_hoy.data[:10], 1):
            estado_icon = "✅" if pub.get('estado') == 'publicada' else "❌"
            print(f"   {i}. {estado_icon} {pub.get('location_name', 'N/A')}")
            print(f"      Hora: {pub.get('published_at', '')[:19]}")
            print(f"      Contenido: {pub.get('contenido', '')[:60]}...")
            if pub.get('estado') == 'error':
                print(f"      Error: {pub.get('error_mensaje', 'N/A')[:80]}")
            print()
    else:
        print("   ℹ️  No se han publicado posts en GBP hoy todavía")
    
    # 3. Publicaciones PENDIENTES (que deberían publicarse)
    print(f"{'='*80}")
    print("⏳ Publicaciones PENDIENTES para GBP (con contenido válido):")
    
    pendientes = supabase.table("meta_publicaciones_webhook")\
        .select("*")\
        .eq("publicada_gbp", False)\
        .not_.is_("mensaje", "null")\
        .gte("creada_en", "2025-12-01")\
        .order("creada_en", desc=True)\
        .limit(20)\
        .execute()
    
    pendientes_validas = []
    for pub in pendientes.data:
        # Verificar si tiene contenido multimedia de Supabase
        for campo in ['imagen_local', 'video_local', 'imagen_url']:
            url = pub.get(campo, '')
            if url and 'supabase' in url.lower() and 'storage' in url.lower():
                pendientes_validas.append(pub)
                break
    
    print(f"   Total pendientes con contenido Supabase: {len(pendientes_validas)}")
    print(f"   Total pendientes sin contenido válido: {len(pendientes.data) - len(pendientes_validas)}\n")
    
    if pendientes_validas:
        print("   Primeras 5 pendientes válidas:")
        for i, pub in enumerate(pendientes_validas[:5], 1):
            print(f"\n   {i}. Post ID: {pub.get('post_id')}")
            print(f"      Fecha: {pub.get('creada_en', '')[:19]}")
            print(f"      Mensaje: {pub.get('mensaje', '')[:60]}...")
            
            # Mostrar qué tipo de contenido tiene
            if pub.get('video_local') and 'supabase' in pub.get('video_local', '').lower():
                print(f"      Tipo: 🎥 VIDEO")
            elif pub.get('imagen_local') and 'supabase' in pub.get('imagen_local', '').lower():
                print(f"      Tipo: 🖼️  IMAGEN")
    
    # 4. Estado del job
    print(f"\n{'='*80}")
    print("⚙️  Estado del Job:")
    job = supabase.table("jobs_config")\
        .select("*")\
        .eq("job_name", "meta_to_gbp_daily")\
        .execute()
    
    if job.data:
        j = job.data[0]
        activo = j.get('is_active', False)
        print(f"   Estado: {'✅ ACTIVO' if activo else '❌ INACTIVO'}")
        print(f"   Intervalo: {j.get('intervalo_minutos', 'N/A')} minutos")
        
        ultima = j.get('last_run_at', '')
        proxima = j.get('next_run_at', '')
        
        if ultima:
            print(f"   Última ejecución: {ultima[:19]}")
        if proxima:
            print(f"   Próxima ejecución: {proxima[:19]}")
    else:
        print("   ⚠️  Job no encontrado")
    
    print("\n" + "="*80)
    
    # Resumen
    print("\n📊 RESUMEN:")
    print(f"   • Publicaciones Facebook recibidas hoy: {len(pubs_facebook_hoy.data)}")
    print(f"   • Publicaciones GBP exitosas hoy: {len([p for p in pubs_gbp_hoy.data if p.get('estado') == 'publicada'])}")
    print(f"   • Publicaciones pendientes (con contenido válido): {len(pendientes_validas)}")
    
    if len(pendientes_validas) > 0 and len(pubs_gbp_hoy.data) == 0:
        print("\n⚠️  ATENCIÓN: Hay publicaciones pendientes pero no se han publicado en GBP hoy.")
        print("   Posibles causas:")
        print("   1. El job no se ha ejecutado hoy")
        print("   2. Las páginas no tienen 'publicar_en_gbp = True'")
        print("   3. Las páginas no tienen 'empresa_id' vinculado")
        print("   4. Error en la ejecución del job")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    try:
        verificar_hoy()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
