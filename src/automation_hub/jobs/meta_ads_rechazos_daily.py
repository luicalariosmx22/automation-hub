"""
Job para detectar anuncios de Meta Ads rechazados.
"""
import logging
from collections import defaultdict
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.meta_ads_anuncios_repo import fetch_anuncios_rechazados_recientes
from automation_hub.db.repositories.alertas_repo import crear_alerta

logger = logging.getLogger(__name__)

JOB_NAME = "meta_ads.rechazos.daily"


def run(ctx=None):
    """
    Ejecuta el job de detección de anuncios rechazados.
    
    1. Consulta anuncios con status DISAPPROVED o REJECTED
    2. Filtra los actualizados en últimas 24h
    3. Agrupa por nombre_nora
    4. Crea alertas por tenant con detalle
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Conectar a Supabase
    logger.info("Conectando a Supabase")
    supabase = create_client_from_env()
    
    # Obtener anuncios rechazados recientes
    logger.info("Obteniendo anuncios rechazados (últimas 24h)")
    anuncios_rechazados = fetch_anuncios_rechazados_recientes(supabase, horas_atras=24)
    
    if not anuncios_rechazados:
        logger.info("No hay anuncios rechazados en las últimas 24h")
        return
    
    # Agrupar por nombre_nora
    rechazos_por_nora = defaultdict(list)
    for anuncio in anuncios_rechazados:
        nombre_nora = anuncio.get("nombre_nora", "Sistema")
        rechazos_por_nora[nombre_nora].append(anuncio)
    
    logger.info(f"Anuncios rechazados agrupados por {len(rechazos_por_nora)} Noras")
    
    # Crear una alerta por cada Nora con anuncios rechazados
    total_alertas = 0
    for nombre_nora, anuncios in rechazos_por_nora.items():
        try:
            # Contar por estado
            por_estado = defaultdict(int)
            for anuncio in anuncios:
                por_estado[anuncio["status"]] += 1
            
            # Generar descripción
            estado_texto = ", ".join([f"{count} {status}" for status, count in por_estado.items()])
            descripcion = (
                f"Se detectaron {len(anuncios)} anuncios rechazados en las últimas 24h: {estado_texto}"
            )
            
            # Preparar datos detallados
            anuncios_detalle = [
                {
                    "id": a["id"],
                    "name": a["name"],
                    "status": a["status"],
                    "cuenta": a.get("id_cuenta_publicitaria"),
                    "campaign_id": a.get("campaign_id"),
                    "updated_time": a.get("updated_time")
                }
                for a in anuncios
            ]
            
            # Crear alerta
            crear_alerta(
                supabase=supabase,
                nombre=f"⚠️ Anuncios Rechazados Meta Ads",
                tipo="meta_ads_rechazados",
                nombre_nora=nombre_nora,
                descripcion=descripcion,
                evento_origen=JOB_NAME,
                datos={
                    "total_rechazados": len(anuncios),
                    "por_estado": dict(por_estado),
                    "anuncios": anuncios_detalle,
                    "job_name": JOB_NAME
                },
                prioridad="alta"  # Rechazos son prioritarios
            )
            
            total_alertas += 1
            logger.info(f"Alerta creada para {nombre_nora}: {len(anuncios)} anuncios rechazados")
        
        except Exception as e:
            logger.error(f"Error creando alerta para {nombre_nora}: {e}", exc_info=True)
            continue
    
    logger.info(f"Job {JOB_NAME} completado. Total alertas creadas: {total_alertas}")
