"""
Cliente para Google Business Profile Performance API v1.
"""
import logging
from datetime import date
from typing import Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


def fetch_multi_daily_metrics(
    location_name: str,
    auth_header: dict,
    metrics: list[str],
    start_date: date,
    end_date: date
) -> list[dict]:
    """
    Obtiene múltiples métricas diarias para una locación usando Performance API v1 con SDK.
    
    Args:
        location_name: Nombre completo de la locación (formato: accounts/*/locations/*)
        auth_header: Dict con header Authorization (contiene el access token)
        metrics: Lista de métricas a obtener (ej: ['WEBSITE_CLICKS', 'CALL_CLICKS'])
        start_date: Fecha inicial del rango
        end_date: Fecha final del rango
        
    Returns:
        Lista de diccionarios raw con las series de tiempo por métrica
    """
    try:
        # Extraer el access token del header
        access_token = auth_header.get('Authorization', '').replace('Bearer ', '')
        
        # Crear credenciales con el access token
        credentials = Credentials(token=access_token)
        
        # Construir el servicio de Business Profile Performance
        service = build('businessprofileperformance', 'v1', credentials=credentials)
        
        all_time_series = []
        
        # Obtener cada métrica individualmente (como en Nora)
        for metric in metrics:
            try:
                request = service.locations().getDailyMetricsTimeSeries(
                    name=location_name,
                    dailyMetric=metric,
                    dailyRange_startDate_year=start_date.year,
                    dailyRange_startDate_month=start_date.month,
                    dailyRange_startDate_day=start_date.day,
                    dailyRange_endDate_year=end_date.year,
                    dailyRange_endDate_month=end_date.month,
                    dailyRange_endDate_day=end_date.day
                )
                
                response = request.execute()
                
                # Agregar el nombre de la métrica a la respuesta
                response['dailyMetric'] = metric
                all_time_series.append(response)
                
            except Exception as e:
                if "404" in str(e):
                    logger.debug(f"Métrica {metric} no disponible para {location_name}")
                else:
                    logger.error(f"Error obteniendo métrica {metric} para {location_name}: {e}")
                continue
        
        logger.info(f"Métricas obtenidas para {location_name}: {len(all_time_series)} series")
        return all_time_series
    
    except Exception as e:
        logger.error(f"Error obteniendo métricas para {location_name}: {e}")
        raise


def parse_metrics_to_rows(
    time_series_list: list[dict],
    nombre_nora: str,
    api_id: str | None,
    location_name: str | None
) -> list[dict]:
    """
    Parsea la respuesta de la API a filas de base de datos.
    
    Args:
        time_series_list: Lista de respuestas getDailyMetricsTimeSeries
        nombre_nora: Tenant de la locación
        api_id: ID de la API de la locación (no usado, compatibilidad)
        location_name: Nombre de la locación
        
    Returns:
        Lista de diccionarios con métricas diarias para insertar en BD
    """
    rows = []
    
    for response in time_series_list:
        metric_name = response.get("dailyMetric")
        time_series = response.get("timeSeries", {})
        daily_values = time_series.get("daysValues", []) or time_series.get("datedValues", [])
        
        for daily_value in daily_values:
            date_dict = daily_value.get("date", {})
            value = daily_value.get("value", 0)
            
            # Convertir value a int si viene como string
            if isinstance(value, str):
                value = int(value) if value else 0
            
            if not date_dict:
                continue
            
            # Construir fecha en formato YYYY-MM-DD
            date_str = f"{date_dict.get('year')}-{date_dict.get('month'):02d}-{date_dict.get('day'):02d}"
            
            rows.append({
                "nombre_nora": nombre_nora,
                "location_name": location_name,
                "metric": metric_name,
                "date": date_str,
                "value": int(value)
            })
    
    logger.debug(f"Filas de métricas parseadas: {len(rows)}")
    return rows
