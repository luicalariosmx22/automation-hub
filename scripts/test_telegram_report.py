"""
Script para analizar los anuncios ya sincronizados y enviar reporte por Telegram (solo análisis, sin sync).
"""
import os
import sys
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Setup
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / 'src'))
load_dotenv(root_dir / '.env')

from automation_hub.jobs.meta_ads_anuncios_daily import (
    obtener_anuncios_sincronizados,
    agrupar_por_cuenta,
    obtener_nombre_cuenta,
    analizar_rendimiento_anuncio,
    generar_mensaje_telegram
)
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.telegram.notifier import TelegramNotifier
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def analizar_y_enviar(fecha):
    """Analiza datos existentes y envía reporte"""
    
    supabase = create_client_from_env()
    telegram = TelegramNotifier()
    
    # Obtener cuentas activas
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria,nombre_cuenta,nombre_nora,cliente_empresas(nombre)') \
        .eq('activo', True) \
        .execute()
    
    cuentas = response.data or []
    logger.info(f"Cuentas activas: {len(cuentas)}")
    
    # Obtener anuncios sincronizados
    logger.info(f"Obteniendo anuncios para fecha: {fecha}")
    anuncios = obtener_anuncios_sincronizados(fecha, supabase)
    logger.info(f"Anuncios encontrados: {len(anuncios)}")
    
    if len(anuncios) == 0:
        logger.warning("No hay anuncios para analizar")
        return
    
    # Agrupar por cuenta
    anuncios_por_cuenta = agrupar_por_cuenta(anuncios)
    
    # Detectar cuentas sin anuncios
    cuentas_sin_anuncios = []
    for cuenta in cuentas:
        cuenta_id = cuenta['id_cuenta_publicitaria']
        if cuenta_id not in anuncios_por_cuenta or len(anuncios_por_cuenta[cuenta_id]) == 0:
            nombre_cuenta = cuenta.get('nombre_nora') or cuenta.get('nombre_cuenta', 'N/A')
            
            # Obtener nombre de empresa
            empresa = cuenta.get('cliente_empresas')
            if empresa and isinstance(empresa, dict):
                nombre_empresa = empresa.get('nombre', 'Sin empresa')
            else:
                nombre_empresa = 'Sin empresa'
            
            nombre_completo = f"{nombre_empresa} - {nombre_cuenta}"
            cuentas_sin_anuncios.append((nombre_completo, cuenta_id))
    
    # Detectar cuentas con 1 solo anuncio
    cuentas_un_anuncio = []
    for cuenta_id, ads in anuncios_por_cuenta.items():
        if len(ads) == 1:
            nombre = obtener_nombre_cuenta(cuenta_id, supabase)
            cuentas_un_anuncio.append((nombre, cuenta_id))
    
    # Analizar rendimiento
    anuncios_buenos = []
    anuncios_malos = []
    
    for anuncio in anuncios:
        estado, score = analizar_rendimiento_anuncio(anuncio)
        anuncio['_score'] = score
        anuncio['_estado'] = estado
        
        if estado == 'malo':
            anuncios_malos.append(anuncio)
        elif estado in ['excelente', 'bueno']:
            anuncios_buenos.append(anuncio)
    
    # Mejores 3
    mejores_anuncios = sorted(anuncios_buenos, key=lambda x: x['_score'], reverse=True)[:3]
    
    logger.info(f"Cuentas sin anuncios: {len(cuentas_sin_anuncios)}")
    logger.info(f"Cuentas con 1 anuncio: {len(cuentas_un_anuncio)}")
    logger.info(f"Anuncios malos: {len(anuncios_malos)}")
    logger.info(f"Anuncios buenos: {len(anuncios_buenos)}")
    
    # Generar mensaje
    mensaje = generar_mensaje_telegram(
        fecha=fecha,
        total_cuentas=len(cuentas),
        total_anuncios=len(anuncios),
        cuentas_sin_anuncios=cuentas_sin_anuncios,
        cuentas_un_anuncio=cuentas_un_anuncio,
        anuncios_malos=anuncios_malos,
        mejores_anuncios=mejores_anuncios
    )
    
    print("\n" + "="*80)
    print("MENSAJE A ENVIAR:")
    print("="*80)
    print(mensaje)
    print("="*80)
    
    # Enviar
    enviado = telegram.enviar_mensaje(mensaje)
    
    if enviado:
        logger.info("✅ Mensaje enviado exitosamente")
    else:
        logger.error("❌ Error al enviar mensaje")

if __name__ == "__main__":
    # Usar fecha de antier (18 de diciembre)
    fecha = date.today() - timedelta(days=2)
    print(f"Analizando datos del: {fecha}")
    analizar_y_enviar(fecha)
