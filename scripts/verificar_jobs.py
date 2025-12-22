"""
Script para verificar el estado REAL de todos los jobs configurados.

Muestra:
- Jobs activos vs inactivos
- Última ejecución de cada job
- Últimos registros insertados en BD
- Notificaciones enviadas
- Errores recientes
- Estado real de funcionamiento
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')

# Agregar src al path
sys.path.insert(0, str(root_dir / 'src'))

from automation_hub.db.supabase_client import create_client_from_env


def formato_duracion(td: timedelta) -> str:
    """Formatea un timedelta de forma legible"""
    if td.total_seconds() < 0:
        return "en el futuro"
    if td.total_seconds() < 60:
        return f"{int(td.total_seconds())}s"
    elif td.total_seconds() < 3600:
        return f"{int(td.total_seconds() / 60)}m"
    elif td.total_seconds() < 86400:
        horas = int(td.total_seconds() / 3600)
        minutos = int((td.total_seconds() % 3600) / 60)
        return f"{horas}h {minutos}m"
    else:
        dias = td.days
        horas = int((td.total_seconds() % 86400) / 3600)
        return f"{dias}d {horas}h"


def obtener_ultimos_registros(supabase, tabla: str, limit: int = 5):
    """Obtiene los últimos registros de una tabla"""
    try:
        response = supabase.table(tabla) \
            .select('*') \
            .order('created_at', desc=True) \
            .limit(limit) \
            .execute()
        return response.data or []
    except Exception as e:
        return []


def verificar_job_gbp_reviews(supabase, ahora):
    """Verifica estado del job de reviews de GBP"""
    print("\n🔍 gbp.reviews.daily")
    print("   " + "-" * 70)
    
    # Últimas reviews sincronizadas
    try:
        response = supabase.table('gbp_reviews') \
            .select('review_id,reviewer_name,update_time') \
            .order('update_time', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            ultimo = response.data[0]
            # update_time puede venir como string
            update_time = ultimo.get('update_time', '')
            if update_time:
                try:
                    fecha = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                    hace = formato_duracion(ahora - fecha)
                    print(f"   ✅ Última review: hace {hace}")
                except:
                    print(f"   ✅ Última review: {update_time}")
            print(f"      Reviewer: {ultimo.get('reviewer_name', 'N/A')}")
        else:
            print(f"   ⚠️  No hay reviews en la BD")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def verificar_job_gbp_metrics(supabase, ahora):
    """Verifica estado del job de métricas de GBP"""
    print("\n🔍 gbp.metrics.daily")
    print("   " + "-" * 70)
    
    try:
        response = supabase.table('gbp_metrics_daily') \
            .select('date,location_name,metric,value') \
            .order('date', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            ultimo = response.data[0]
            print(f"   ✅ Última métrica: {ultimo.get('date', 'N/A')}")
            print(f"      Location: {ultimo.get('location_name', 'N/A')[:40]}")
            print(f"      Métrica: {ultimo.get('metric', 'N/A')} = {ultimo.get('value', 0)}")
        else:
            print(f"   ⚠️  No hay métricas en la BD")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def verificar_job_calendar_sync(supabase, ahora):
    """Verifica estado del job de sincronización de calendario"""
    print("\n🔍 calendar.sync")
    print("   " + "-" * 70)
    
    try:
        # Citas sincronizadas de Google Calendar
        response = supabase.table('agenda_citas') \
            .select('*') \
            .eq('origen', 'google_calendar') \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            ultimo = response.data[0]
            fecha = datetime.fromisoformat(ultimo['created_at'].replace('Z', '+00:00'))
            hace = formato_duracion(ahora - fecha)
            print(f"   ✅ Última cita sincronizada: hace {hace}")
            print(f"      Título: {ultimo.get('titulo', 'N/A')}")
        else:
            print(f"   ⚠️  No hay citas de Google Calendar en la BD")
            
        # Total de citas de Google Calendar
        response = supabase.table('agenda_citas') \
            .select('id', count='exact') \
            .eq('origen', 'google_calendar') \
            .execute()
        
        total = response.count or 0
        print(f"   📊 Total de citas de Google Calendar: {total}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def verificar_job_calendar_summary(supabase, ahora):
    """Verifica estado del job de resumen diario de calendario"""
    print("\n🔍 calendar.daily.summary")
    print("   " + "-" * 70)
    
    # Este job envía notificaciones por Telegram
    # Podemos ver cuántas citas tiene hoy
    try:
        hoy = ahora.date().isoformat()
        response = supabase.table('agenda_citas') \
            .select('id', count='exact') \
            .gte('inicio', f'{hoy}T00:00:00') \
            .lte('inicio', f'{hoy}T23:59:59') \
            .execute()
        
        total_hoy = response.count or 0
        print(f"   📊 Citas programadas para hoy: {total_hoy}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def verificar_job_meta_ads_cuentas(supabase, ahora):
    """Verifica estado del job de sincronización de cuentas Meta Ads"""
    print("\n🔍 meta_ads.cuentas.sync.daily")
    print("   " + "-" * 70)
    
    try:
        # Última cuenta actualizada
        response = supabase.table('meta_ads_cuentas') \
            .select('id_cuenta_publicitaria,nombre_cuenta,actualizada_en') \
            .order('actualizada_en', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            ultimo = response.data[0]
            fecha_act = ultimo.get('actualizada_en')
            if fecha_act:
                try:
                    fecha = datetime.fromisoformat(fecha_act.replace('Z', '+00:00'))
                    hace = formato_duracion(ahora - fecha)
                    print(f"   ✅ Última actualización: hace {hace}")
                except:
                    print(f"   ✅ Última actualización: {fecha_act}")
            print(f"      Cuenta: {ultimo.get('nombre_cuenta', 'N/A')}")
        
        # Total de cuentas activas
        response = supabase.table('meta_ads_cuentas') \
            .select('id', count='exact') \
            .eq('activo', True) \
            .execute()
        
        total = response.count or 0
        print(f"   📊 Total de cuentas activas: {total}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
def verificar_job_meta_ads_anuncios(supabase, ahora):
    """Verifica estado del job de sincronización de anuncios Meta Ads"""
    print("\n🔍 meta_ads.anuncios.daily")
    print("   " + "-" * 70)
    
    try:
        response = supabase.table('meta_ads_anuncios_daily') \
            .select('ad_id,nombre_anuncio,fecha_reporte,fecha_sincronizacion') \
            .order('fecha_sincronizacion', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            ultimo = response.data[0]
            fecha_sync = ultimo.get('fecha_sincronizacion')
            if fecha_sync:
                try:
                    fecha = datetime.fromisoformat(fecha_sync.replace('Z', '+00:00'))
                    hace = formato_duracion(ahora - fecha)
                    print(f"   ✅ Última sincronización: hace {hace}")
                except:
                    print(f"   ✅ Última sincronización: {fecha_sync}")
            print(f"      Anuncio: {ultimo.get('nombre_anuncio', 'N/A')[:50]}")
            print(f"      Fecha reporte: {ultimo.get('fecha_reporte', 'N/A')}")
        else:
            print(f"   ⚠️  No hay anuncios en la BD")
            
        # Anuncios del día anterior
        ayer = (ahora - timedelta(days=1)).date().isoformat()
        response = supabase.table('meta_ads_anuncios_daily') \
            .select('id', count='exact') \
            .eq('fecha_reporte', ayer) \
            .execute()
        
        total_ayer = response.count or 0
        print(f"   📊 Anuncios sincronizados de ayer ({ayer}): {total_ayer}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def verificar_job_meta_ads_rechazos(supabase, ahora):
    """Verifica estado del job de rechazos de Meta Ads"""
    print("\n🔍 meta_ads.rechazos.daily")
    print("   " + "-" * 70)
    
    try:
        # Este job puede no tener tabla propia, solo envía notificaciones
        print(f"   ℹ️  Job de notificaciones (sin tabla específica)")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")


def main():
    """Función principal"""
    print("=" * 80)
    print("📋 VERIFICACIÓN COMPLETA DE JOBS - AUTOMATION HUB")
    print("=" * 80)
    print()
    
    try:
        supabase = create_client_from_env()
        ahora = datetime.now(timezone.utc)
        
        # 1. Obtener configuración de jobs
        response = supabase.table('jobs_config') \
            .select('*') \
            .order('job_name') \
            .execute()
        
        jobs = response.data
        
        if not jobs:
            print("⚠️  No se encontraron jobs configurados")
            return
        
        # 2. Estadísticas generales
        total_jobs = len(jobs)
        jobs_activos = sum(1 for j in jobs if j.get('enabled'))
        
        print(f"📊 RESUMEN GENERAL")
        print("-" * 80)
        print(f"Total de jobs: {total_jobs}")
        print(f"✅ Activos: {jobs_activos}")
        print(f"❌ Inactivos: {total_jobs - jobs_activos}")
        print()
        
        # 3. Estado básico de cada job
        print(f"⏰ ESTADO DE EJECUCIÓN")
        print("-" * 80)
        
        for job in jobs:
            nombre = job.get('job_name', 'Sin nombre')
            enabled = job.get('enabled', False)
            intervalo = job.get('schedule_interval_minutes', 0)
            ultima_ejecucion = job.get('last_run_at')
            
            icono = "✅" if enabled else "❌"
            print(f"\n{icono} {nombre}")
            
            if ultima_ejecucion:
                try:
                    fecha = datetime.fromisoformat(ultima_ejecucion.replace('Z', '+00:00'))
                    hace = formato_duracion(ahora - fecha)
                    print(f"   ⏰ Última ejecución: hace {hace}")
                except:
                    print(f"   ⏰ Última ejecución: {ultima_ejecucion}")
            else:
                print(f"   ⚠️  Nunca ejecutado")
        
        print()
        print()
        
        # 4. Verificación profunda de cada job
        print("=" * 80)
        print("🔬 VERIFICACIÓN PROFUNDA - DATOS EN BD")
        print("=" * 80)
        
        verificar_job_gbp_reviews(supabase, ahora)
        verificar_job_gbp_metrics(supabase, ahora)
        verificar_job_calendar_sync(supabase, ahora)
        verificar_job_calendar_summary(supabase, ahora)
        verificar_job_meta_ads_cuentas(supabase, ahora)
        verificar_job_meta_ads_anuncios(supabase, ahora)
        verificar_job_meta_ads_rechazos(supabase, ahora)
        
        print()
        print("=" * 80)
        print("✅ Verificación completada")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error al verificar jobs: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
