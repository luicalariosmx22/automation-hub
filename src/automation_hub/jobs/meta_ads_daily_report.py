"""
Job para analizar anuncios de Meta Ads y enviar reporte diario por Telegram.

Este job NO sincroniza datos, solo analiza lo que ya está en la BD.
"""
import logging
import os
from datetime import date, timedelta
from typing import Dict, List, Tuple
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.telegram.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

JOB_NAME = "meta_ads.daily_report"


def analizar_rendimiento_anuncio(anuncio: dict) -> Tuple[str, float]:
    """
    Analiza el rendimiento de un anuncio y devuelve su calificación.
    
    Criterios:
    - CTR >2% excelente, 1-2% bueno, <1% malo
    - CPC <$0.50 excelente, $0.50-$1.00 bueno, >$1.00 malo
    - Alcance >1000 excelente, 500-1000 bueno, <500 malo
    
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


def run(ctx=None):
    """
    Ejecuta el análisis de anuncios Meta Ads y envía reporte por Telegram.
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Fecha a analizar (ayer)
    fecha = date.today() - timedelta(days=1)
    logger.info(f"Analizando anuncios para fecha: {fecha}")
    
    supabase = create_client_from_env()
    telegram = TelegramNotifier()
    
    # 1. Obtener todas las cuentas activas con nombre de empresa
    logger.info("Obteniendo cuentas activas...")
    cuentas_response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_cuenta,nombre_nora,nombre_empresa') \
        .eq('activo', True) \
        .eq('estado_actual', 'ACTIVE') \
        .execute()
    
    cuentas = cuentas_response.data or []
    logger.info(f"Cuentas activas: {len(cuentas)}")
    
    # 2. Obtener anuncios del día
    logger.info("Obteniendo anuncios sincronizados...")
    anuncios_response = supabase.table('meta_ads_anuncios_daily') \
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
    
    anuncios = anuncios_response.data or []
    logger.info(f"Anuncios encontrados: {len(anuncios)}")
    
    if len(anuncios) == 0:
        mensaje = f"⚠️ No hay datos de Meta Ads para {fecha.strftime('%d/%m/%Y')}"
        telegram.enviar_mensaje(mensaje)
        logger.warning("No hay datos para analizar")
        return {'ok': True, 'mensaje': 'Sin datos'}
    
    # 3. Agrupar anuncios por cuenta
    anuncios_por_cuenta = {}
    for anuncio in anuncios:
        cuenta_id = anuncio['id_cuenta_publicitaria']
        if cuenta_id not in anuncios_por_cuenta:
            anuncios_por_cuenta[cuenta_id] = []
        anuncios_por_cuenta[cuenta_id].append(anuncio)
    
    # 3b. Crear resumen por empresa
    resumen_por_empresa = {}
    for cuenta in cuentas:
        cuenta_id = cuenta['id_cuenta_publicitaria']
        if cuenta_id in anuncios_por_cuenta:
            # Obtener nombre de empresa
            nombre_empresa = cuenta.get('nombre_empresa')
            if nombre_empresa and nombre_empresa.strip():
                nombre = nombre_empresa.strip()
            else:
                # Usar nombre_cuenta (nombre real de Meta Ads) como fallback
                nombre = cuenta.get('nombre_cuenta') or f"Cuenta {cuenta_id}"
            
            # Sumar anuncios y gasto de esta cuenta
            ads = anuncios_por_cuenta[cuenta_id]
            num_anuncios = len(ads)
            gasto_total = sum(float(ad.get('importe_gastado', 0) or 0) for ad in ads)
            
            if nombre not in resumen_por_empresa:
                resumen_por_empresa[nombre] = {'anuncios': 0, 'gasto': 0}
            
            resumen_por_empresa[nombre]['anuncios'] += num_anuncios
            resumen_por_empresa[nombre]['gasto'] += gasto_total
    
    # 4. Detectar cuentas sin anuncios
    cuentas_sin_anuncios = []
    for cuenta in cuentas:
        cuenta_id = cuenta['id_cuenta_publicitaria']
        if cuenta_id not in anuncios_por_cuenta:
            # Priorizar nombre_empresa, si no existe usar nombre_cuenta
            nombre_empresa = cuenta.get('nombre_empresa')
            if nombre_empresa and nombre_empresa.strip():
                cuentas_sin_anuncios.append(nombre_empresa.strip())
            else:
                # Usar nombre_cuenta (nombre real de Meta Ads) como fallback
                nombre_cuenta = cuenta.get('nombre_cuenta') or f"Cuenta {cuenta_id}"
                cuentas_sin_anuncios.append(nombre_cuenta)
    
    # 5. Detectar cuentas con solo 1 anuncio
    cuentas_un_anuncio = []
    for cuenta_id, ads in anuncios_por_cuenta.items():
        if len(ads) == 1:
            # Buscar nombre de la cuenta
            cuenta = next((c for c in cuentas if c['id_cuenta_publicitaria'] == cuenta_id), None)
            if cuenta:
                # Priorizar nombre_empresa, si no existe usar nombre_cuenta
                nombre_empresa = cuenta.get('nombre_empresa')
                if nombre_empresa and nombre_empresa.strip():
                    cuentas_un_anuncio.append(nombre_empresa.strip())
                else:
                    # Usar nombre_cuenta (nombre real de Meta Ads) como fallback
                    cuenta_id = cuenta.get('id_cuenta_publicitaria')
                    nombre_cuenta = cuenta.get('nombre_cuenta') or f"Cuenta {cuenta_id}"
                    cuentas_un_anuncio.append(nombre_cuenta)
    
    logger.info(f"Cuentas sin anuncios: {len(cuentas_sin_anuncios)}")
    logger.info(f"Cuentas con 1 anuncio: {len(cuentas_un_anuncio)}")
    
    # 8. Generar mensaje de Telegram
    mensaje = f"📊 <b>META ADS - Reporte Diario</b>\n"
    mensaje += f"📅 Fecha: {fecha.strftime('%d/%m/%Y')}\n"
    mensaje += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Resumen general
    mensaje += f"✅ Cuentas activas: {len(cuentas)}\n"
    mensaje += f"📢 Total anuncios: {len(anuncios)}\n\n"
    
    # Resumen por empresa
    if resumen_por_empresa:
        mensaje += f"💼 <b>Anuncios por Empresa</b>\n"
        # Ordenar por gasto descendente
        empresas_ordenadas = sorted(resumen_por_empresa.items(), 
                                    key=lambda x: x[1]['gasto'], 
                                    reverse=True)
        for nombre, datos in empresas_ordenadas:
            num_ads = datos['anuncios']
            gasto = datos['gasto']
            mensaje += f"   • {nombre}: {num_ads} anuncio{'s' if num_ads != 1 else ''} - ${gasto:,.2f}\n"
        mensaje += "\n"
    
    # Cuentas sin anuncios
    if cuentas_sin_anuncios:
        mensaje += f"⚠️ <b>Cuentas SIN anuncios ({len(cuentas_sin_anuncios)})</b>\n"
        for nombre in cuentas_sin_anuncios:
            mensaje += f"   • {nombre}\n"
        mensaje += "\n"
    
    # Cuentas con solo 1 anuncio
    if cuentas_un_anuncio:
        mensaje += f"⚡ <b>Cuentas con 1 solo anuncio ({len(cuentas_un_anuncio)})</b>\n"
        for nombre in cuentas_un_anuncio:
            mensaje += f"   • {nombre}\n"
        mensaje += "\n"
    
    mensaje += f"━━━━━━━━━━━━━━━━━━━━\n"
    mensaje += f"🤖 Automation Hub"
    
    # 9. Enviar mensaje por Telegram a todos los destinatarios
    logger.info("Enviando reporte por Telegram...")
    
    # Obtener todos los destinatarios activos para meta_ads
    destinatarios_response = supabase.table('notificaciones_telegram_config') \
        .select('chat_id') \
        .eq('activo', True) \
        .execute()
    
    destinatarios = destinatarios_response.data or []
    
    if not destinatarios:
        logger.warning("No hay destinatarios configurados para notificaciones")
        # Enviar al chat por defecto como fallback
        enviado = telegram.enviar_mensaje(mensaje)
    else:
        enviados = 0
        for dest in destinatarios:
            chat_id = dest.get('chat_id')
            
            if telegram.enviar_mensaje(mensaje, chat_id=chat_id):
                logger.info(f"✅ Mensaje enviado a chat {chat_id}")
                enviados += 1
            else:
                logger.error(f"❌ Error al enviar a chat {chat_id}")
        
        enviado = enviados > 0
        logger.info(f"Reporte enviado a {enviados}/{len(destinatarios)} destinatarios")
    
    if enviado:
        logger.info("✅ Reporte enviado exitosamente")
    else:
        logger.error("❌ Error al enviar reporte")
    
    logger.info(f"Job completado: {JOB_NAME}")
    
    return {
        'ok': True,
        'total_cuentas': len(cuentas),
        'total_anuncios': len(anuncios),
        'cuentas_sin_anuncios': len(cuentas_sin_anuncios),
        'cuentas_un_anuncio': len(cuentas_un_anuncio),
        'mensaje_enviado': enviado
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
