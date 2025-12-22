"""
Job para sincronizar anuncios de Meta Ads diariamente.

Este job:
1. Sincroniza todos los anuncios del día anterior
2. Guarda los datos en la tabla meta_ads_anuncios_daily
3. Envía notificación simple de confirmación

El reporte completo lo envía meta_ads_daily_report.py
"""
import logging
import os
from datetime import date, timedelta
from typing import Dict, List, Sequence, Tuple, cast
from automation_hub.integrations.meta_ads.daily_sync_service import MetaAdsDailySyncService
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.telegram.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "meta_ads.anuncios.daily"


def analizar_rendimiento_anuncio(anuncio: dict) -> Tuple[str, float]:
    """
    Analiza el rendimiento de un anuncio y devuelve su calificación.
    
    Criterios:
    - CTR (Click-Through Rate): >2% excelente, 1-2% bueno, <1% malo
    - CPC (Cost Per Click): <$0.50 excelente, $0.50-$1.00 bueno, >$1.00 malo
    - Alcance: >1000 excelente, 500-1000 bueno, <500 malo
    - Gasto vs Resultados: ROI básico
    
    Returns:
        Tuple[estado, score] donde estado es 'excelente', 'bueno', 'malo'
        y score es un valor de 0-100
    """
    score = 0
    impresiones = anuncio.get('impresiones', 0) or 0
    clicks = anuncio.get('clicks', 0) or 0
    alcance = anuncio.get('alcance', 0) or 0
    gasto = float(anuncio.get('importe_gastado', 0) or 0)
    
    # Mínimo de impresiones para evaluar
    if impresiones < 100:
        return 'sin_datos', 0
    
    # CTR (40 puntos)
    ctr = (clicks / impresiones * 100) if impresiones > 0 else 0
    if ctr >= 2:
        score += 40
    elif ctr >= 1:
        score += 25
    elif ctr >= 0.5:
        score += 15
    else:
        score += 5
    
    # CPC (30 puntos)
    cpc = (gasto / clicks) if clicks > 0 else 999
    if cpc <= 0.50:
        score += 30
    elif cpc <= 1.00:
        score += 20
    elif cpc <= 2.00:
        score += 10
    else:
        score += 0
    
    # Alcance (20 puntos)
    if alcance >= 1000:
        score += 20
    elif alcance >= 500:
        score += 12
    elif alcance >= 100:
        score += 5
    
    # Engagement (10 puntos) - relación clicks/alcance
    engagement = (clicks / alcance * 100) if alcance > 0 else 0
    if engagement >= 5:
        score += 10
    elif engagement >= 2:
        score += 5
    
    # Clasificación
    if score >= 70:
        return 'excelente', score
    elif score >= 50:
        return 'bueno', score
    else:
        return 'malo', score


def obtener_anuncios_sincronizados(fecha: date, supabase) -> List[dict]:
    """
    Obtiene todos los anuncios sincronizados para una fecha.
    
    Returns:
        Lista de anuncios con sus métricas
    """
    response = supabase.table('meta_ads_anuncios_daily') \
        .select('''
            id_cuenta_publicitaria,
            ad_id,
            nombre_anuncio,
            publisher_platform,
            impresiones,
            clicks,
            alcance,
            importe_gastado
        ''') \
        .eq('fecha_reporte', str(fecha)) \
        .execute()
    
    return response.data or []


def agrupar_por_cuenta(anuncios: List[dict]) -> Dict[str, List[dict]]:
    """
    Agrupa los anuncios por cuenta publicitaria.
    """
    cuentas = {}
    for anuncio in anuncios:
        cuenta_id = anuncio['id_cuenta_publicitaria']
        if cuenta_id not in cuentas:
            cuentas[cuenta_id] = []
        cuentas[cuenta_id].append(anuncio)
    return cuentas


def obtener_nombre_cuenta(cuenta_id: str, supabase) -> str:
    """
    Obtiene el nombre de una cuenta.
    """
    response = supabase.table('meta_ads_cuentas') \
        .select('nombre_cuenta,nombre_nora') \
        .eq('id_cuenta_publicitaria', cuenta_id) \
        .limit(1) \
        .execute()
    
    if response.data:
        cuenta = response.data[0]
        nombre_cuenta = cuenta.get('nombre_nora') or cuenta.get('nombre_cuenta', 'Sin nombre')
        return nombre_cuenta
    return f"Cuenta {cuenta_id[-8:]}"


def generar_mensaje_telegram(
    fecha: date,
    total_cuentas: int,
    total_anuncios: int,
    cuentas_sin_anuncios: List[Tuple[str, str]],
    cuentas_un_anuncio: List[Tuple[str, str]],
    anuncios_malos: List[dict],
    mejores_anuncios: List[dict]
) -> str:
    """
    Genera el mensaje formateado para Telegram.
    """
    mensaje = f"📊 <b>META ADS - Reporte Diario</b>\n"
    mensaje += f"📅 Fecha: {fecha.strftime('%d/%m/%Y')}\n"
    mensaje += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Resumen general
    mensaje += f"✅ Cuentas sincronizadas: {total_cuentas}\n"
    mensaje += f"📢 Total anuncios: {total_anuncios}\n\n"
    
    # Cuentas sin anuncios
    if cuentas_sin_anuncios:
        mensaje += f"⚠️ <b>Cuentas SIN anuncios ({len(cuentas_sin_anuncios)})</b>\n"
        for nombre, cuenta_id in cuentas_sin_anuncios[:5]:  # Máximo 5
            mensaje += f"   • {nombre}\n"
        if len(cuentas_sin_anuncios) > 5:
            mensaje += f"   ... y {len(cuentas_sin_anuncios) - 5} más\n"
        mensaje += "\n"
    
    # Cuentas con solo 1 anuncio
    if cuentas_un_anuncio:
        mensaje += f"⚡ <b>Cuentas con 1 solo anuncio ({len(cuentas_un_anuncio)})</b>\n"
        for nombre, cuenta_id in cuentas_un_anuncio[:5]:  # Máximo 5
            mensaje += f"   • {nombre}\n"
        if len(cuentas_un_anuncio) > 5:
            mensaje += f"   ... y {len(cuentas_un_anuncio) - 5} más\n"
        mensaje += "\n"
    
    # Anuncios con mal rendimiento
    if anuncios_malos:
        mensaje += f"🔴 <b>Anuncios con MAL rendimiento ({len(anuncios_malos)})</b>\n"
        for anuncio in anuncios_malos[:3]:  # Top 3 peores
            nombre = anuncio['nombre_anuncio'][:30]
            impresiones = anuncio.get('impresiones', 0) or 0
            clicks = anuncio.get('clicks', 0) or 0
            ctr = (clicks / impresiones * 100) if impresiones > 0 else 0
            gasto = float(anuncio.get('importe_gastado', 0) or 0)
            
            mensaje += f"   • {nombre}\n"
            mensaje += f"     👁 {impresiones:,} imp | 👆 {clicks} clicks | "
            mensaje += f"CTR: {ctr:.2f}% | ${gasto:.2f}\n"
        if len(anuncios_malos) > 3:
            mensaje += f"   ... y {len(anuncios_malos) - 3} más con bajo rendimiento\n"
        mensaje += "\n"
    
    # Mejores anuncios
    if mejores_anuncios:
        mensaje += f"🏆 <b>TOP 3 Mejores Anuncios</b>\n"
        for i, anuncio in enumerate(mejores_anuncios[:3], 1):
            nombre = anuncio['nombre_anuncio'][:30]
            impresiones = anuncio.get('impresiones', 0) or 0
            clicks = anuncio.get('clicks', 0) or 0
            alcance = anuncio.get('alcance', 0) or 0
            ctr = (clicks / impresiones * 100) if impresiones > 0 else 0
            gasto = float(anuncio.get('importe_gastado', 0) or 0)
            score = anuncio.get('_score', 0)
            
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            mensaje += f"\n{emoji} <b>#{i} {nombre}</b>\n"
            mensaje += f"   📊 Score: {score:.0f}/100\n"
            mensaje += f"   👁 {impresiones:,} impresiones\n"
            mensaje += f"   👆 {clicks} clicks (CTR: {ctr:.2f}%)\n"
            mensaje += f"   👥 {alcance:,} alcance\n"
            mensaje += f"   💰 ${gasto:.2f}\n"
    
    mensaje += f"\n━━━━━━━━━━━━━━━━━━━━\n"
    mensaje += f"🤖 Automation Hub"
    
    return mensaje


def run(ctx=None):
    """
    Ejecuta el job de sincronización de anuncios Meta Ads.
    Sincroniza datos y envía notificación simple.
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Fecha a sincronizar (ayer - día anterior)
    fecha = date.today() - timedelta(days=1)
    
    logger.info(f"Sincronizando anuncios para fecha: {fecha}")
    
    # Crear clientes
    supabase = create_client_from_env()
    service = MetaAdsDailySyncService()
    telegram = TelegramNotifier()
    
    # Obtener cuentas activas
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_cuenta,nombre_nora,empresa_id') \
        .eq('activo', True) \
        .execute()
    
    cuentas = cast(List[dict], response.data) if response.data else []
    logger.info(f"Cuentas activas: {len(cuentas)}")
    
    # Sincronizar cada cuenta
    total_anuncios = 0
    errores = 0
    
    for i, cuenta in enumerate(cuentas, 1):
        account_id = cuenta['id_cuenta_publicitaria']
        nombre = cuenta.get('nombre_nora') or cuenta.get('nombre_cuenta', 'N/A')
        
        logger.info(f"[{i}/{len(cuentas)}] Sincronizando {nombre} ({account_id})")
        
        try:
            result = service.sync_account_daily(
                account_id=account_id,
                fecha_reporte=fecha,
                nombre_nora=nombre
            )
            
            if result.get('ok'):
                procesados = result.get('processed', 0)
                total_anuncios += procesados
                logger.info(f"  ✓ {procesados} anuncios procesados")
            else:
                errores += 1
                logger.warning(f"  ✗ Error en sincronización")
                
        except Exception as e:
            errores += 1
            logger.error(f"  ✗ Error: {str(e)}")
    
    logger.info(f"Sincronización completada: {total_anuncios} anuncios, {errores} errores")
    
    # Enviar notificación simple
    logger.info("Enviando notificación de confirmación...")
    
    icono = "✅" if errores == 0 else "⚠️"
    mensaje = f"{icono} <b>Sincronización Meta Ads</b>\n"
    mensaje += f"📅 Fecha: {fecha.strftime('%d/%m/%Y')}\n\n"
    mensaje += f"📊 Cuentas procesadas: {len(cuentas)}\n"
    mensaje += f"📢 Anuncios sincronizados: {total_anuncios}\n"
    
    if errores > 0:
        mensaje += f"⚠️ Errores: {errores}\n"
    
    mensaje += f"\n🤖 Job: meta_ads.anuncios.daily"
    
    enviado = telegram.enviar_mensaje(mensaje)
    
    if enviado:
        logger.info("✓ Notificación enviada")
    else:
        logger.error("✗ Error al enviar notificación")
    
    logger.info(f"Job completado: {JOB_NAME}")
    
    return {
        'ok': True,
        'total_cuentas': len(cuentas),
        'total_anuncios': total_anuncios,
        'errores': errores,
        'notificacion_enviada': enviado
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Setup para ejecución directa
    root_dir = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(root_dir / 'src'))
    load_dotenv(root_dir / '.env')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run()
