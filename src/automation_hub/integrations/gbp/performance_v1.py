"""
Cliente para Google Business Profile Performance API v1.
"""
import logging
import requests
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


def fetch_multi_daily_metrics(
    location_id: str,
    token: str,
    metrics: list[str],
    start_date: date,
    end_date: date
) -> list[dict]:
    """
    Obtiene múltiples métricas diarias para una locación usando Performance API v1.
    
    Args:
        location_id: ID de la locación (formato: locations/*)
        token: Bearer token de acceso
        metrics: Lista de métricas a obtener (ej: ['WEBSITE_CLICKS', 'CALL_CLICKS'])
        start_date: Fecha inicial del rango
        end_date: Fecha final del rango
        
    Returns:
        Lista de diccionarios raw con las series de tiempo por métrica
    """
    base_url = "https://businessprofileperformance.googleapis.com/v1"
    url = f"{base_url}/{location_id}:fetchMultiDailyMetricsTimeSeries"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Construir query params para cada métrica
    params = []
    for metric in metrics:
        params.append(("dailyMetrics", metric))
    
    # Agregar rango de fechas
    params.extend([
        ("dailyRange.start_date.year", start_date.year),
        ("dailyRange.start_date.month", start_date.month),
        ("dailyRange.start_date.day", start_date.day),
        ("dailyRange.end_date.year", end_date.year),
        ("dailyRange.end_date.month", end_date.month),
        ("dailyRange.end_date.day", end_date.day)
    ])
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        time_series = data.get("multiDailyMetricTimeSeries", [])
        
        logger.info(f"Métricas obtenidas para {location_id}: {len(time_series)} series")
        return time_series
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error obteniendo métricas para {location_id}: {e}")
        raise


def parse_metrics_to_rows(
    time_series_list: list[dict],
    nombre_nora: str,
    api_id: str,
    location_name: str
) -> list[dict]:
    """
    Parsea la respuesta de la API a filas de base de datos.
    
    Args:
        time_series_list: Lista de series de tiempo de la API
        nombre_nora: Tenant de la locación
        api_id: ID de la API de la locación
        location_name: Nombre de la locación
        
    Returns:
        Lista de diccionarios con métricas diarias para insertar en BD
    """
    rows = []
    
    for series in time_series_list:
        metric_name = series.get("dailyMetric")
        daily_metric_time_series = series.get("dailyMetricTimeSeries", {})
        time_series_data = daily_metric_time_series.get("timeSeries", {})
        daily_values = time_series_data.get("datedValues", [])
        
        for daily_value in daily_values:
            date_dict = daily_value.get("date", {})
            value = daily_value.get("value", 0)
            
            # Construir fecha en formato YYYY-MM-DD
            date_str = f"{date_dict.get('year')}-{date_dict.get('month'):02d}-{date_dict.get('day'):02d}"
            
            rows.append({
                "nombre_nora": nombre_nora,
                "api_id": api_id,
                "location_name": location_name,
                "metric": metric_name,
                "date": date_str,
                "value": int(value)
            })
    
    logger.debug(f"Filas de métricas parseadas: {len(rows)}")
    return rows
