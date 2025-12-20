"""
Servicio para sincronizar datos demográficos y geográficos de Meta Ads.
Este servicio actualiza registros existentes en meta_ads_anuncios_daily
agregando información de age, gender, region, country, device_platform.
"""
import os
import json
import logging
from datetime import date, datetime
from typing import Dict, List, Optional
import requests

from src.automation_hub.db.supabase_client import create_client_from_env

logger = logging.getLogger(__name__)


class MetaAdsDemographicSyncService:
    """
    Servicio para sincronizar datos demográficos de Meta Ads.
    
    Importante: Este servicio NO usa action_breakdowns para poder
    obtener datos demográficos (age, gender, region, etc.)
    """
    
    BASE_URL = "https://graph.facebook.com/v23.0"
    LOG_EVERY = 50
    
    # Campos básicos SIN actions (incompatible con breakdowns demográficos)
    INSIGHT_FIELDS = [
        "date_start", "date_stop", "account_id", "campaign_id", "adset_id", "ad_id",
        "ad_name", "adset_name", "campaign_name",
        "impressions", "reach", "clicks", "spend",
        "cpm", "cpc", "ctr", "frequency"
    ]
    
    def __init__(self, supabase_client=None):
        """Initialize service with Supabase client"""
        self.supabase = supabase_client or create_client_from_env()
        self.access_token = os.getenv('META_ACCESS_REDACTED_TOKEN')
        if not self.access_token:
            raise ValueError("META_ACCESS_REDACTED_TOKEN environment variable is required")
    
    @staticmethod
    def normalize_account_id(account_id: str) -> str:
        """Normaliza ID de cuenta removiendo prefijo 'act_' si existe"""
        return account_id.replace('act_', '') if account_id else account_id
    
    def get_demographic_insights(
        self,
        account_id: str,
        fecha: date,
        breakdown: str
    ) -> List[Dict]:
        """
        Obtiene insights con un breakdown demográfico específico.
        
        Args:
            account_id: ID de la cuenta
            fecha: Fecha a sincronizar
            breakdown: age, gender, region, country, device_platform, impression_device
            
        Returns:
            Lista de insights
        """
        base_account_id = self.normalize_account_id(account_id)
        url = f"{self.BASE_URL}/act_{base_account_id}/insights"
        
        params = {
            'access_token': self.access_token,
            'level': 'ad',
            'breakdowns': breakdown,  # Solo breakdown demográfico
            # NO usar action_breakdowns
            'time_range': json.dumps({
                'since': fecha.strftime('%Y-%m-%d'),
                'until': fecha.strftime('%Y-%m-%d')
            }),
            'fields': ','.join(self.INSIGHT_FIELDS),
            'limit': 500,
        }
        
        all_insights = []
        
        try:
            while url:
                response = requests.get(url, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()
                
                insights = data.get('data', [])
                all_insights.extend(insights)
                
                # Paginación
                url = data.get('paging', {}).get('next')
                params = {}  # Los params ya están en la URL next
                
                if len(all_insights) % self.LOG_EVERY == 0:
                    logger.info(f"   Obtenidos {len(all_insights)} insights con breakdown {breakdown}")
            
            return all_insights
            
        except Exception as e:
            logger.error(f"Error obteniendo insights demográficos: {e}")
            return []
    
    def update_demographic_data(
        self,
        account_id: str,
        fecha: date,
        breakdown_field: str,
        insights: List[Dict]
    ) -> int:
        """
        Actualiza registros existentes con datos demográficos.
        
        Args:
            account_id: ID de cuenta
            fecha: Fecha de los datos
            breakdown_field: Campo a actualizar (age, gender, region, etc.)
            insights: Insights obtenidos de la API
            
        Returns:
            Cantidad de registros actualizados
        """
        updated = 0
        errors = []
        
        for insight in insights:
            ad_id = insight.get('ad_id')
            breakdown_value = insight.get(breakdown_field)
            
            if not ad_id or not breakdown_value:
                continue
            
            try:
                # Actualizar TODOS los registros (todas las plataformas) de este ad_id en esta fecha
                result = self.supabase.table('meta_ads_anuncios_daily') \
                    .update({breakdown_field: breakdown_value}) \
                    .eq('ad_id', str(ad_id)) \
                    .eq('fecha_reporte', fecha.isoformat()) \
                    .eq('id_cuenta_publicitaria', account_id) \
                    .execute()
                
                if result.data:
                    updated += len(result.data)
                    
            except Exception as e:
                error_msg = f"Error actualizando {breakdown_field} para ad {ad_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        if errors:
            logger.warning(f"Errores actualizando {breakdown_field}: {len(errors)}")
        
        return updated
    
    def sync_account_demographics(
        self,
        account_id: str,
        fecha: date,
        breakdowns: Optional[List[str]] = None
    ) -> Dict:
        """
        Sincroniza datos demográficos para una cuenta.
        
        Args:
            account_id: ID de cuenta publicitaria
            fecha: Fecha a sincronizar
            breakdowns: Lista de breakdowns a sincronizar 
                       (por defecto: age, gender, region, device_platform)
            
        Returns:
            Dict con resultados de la sincronización
        """
        if breakdowns is None:
            breakdowns = ['age', 'gender', 'region', 'device_platform']
        
        logger.info(f"🔄 Sincronizando demográficos: {account_id} - {fecha}")
        
        results = {
            'ok': True,
            'account_id': account_id,
            'fecha': fecha.isoformat(),
            'breakdowns': {}
        }
        
        for breakdown in breakdowns:
            logger.info(f"   📊 Procesando breakdown: {breakdown}")
            
            # Obtener insights
            insights = self.get_demographic_insights(account_id, fecha, breakdown)
            
            if not insights:
                logger.info(f"   ℹ️ No hay datos para {breakdown}")
                results['breakdowns'][breakdown] = {'insights': 0, 'updated': 0}
                continue
            
            logger.info(f"   ✅ Obtenidos {len(insights)} insights para {breakdown}")
            
            # Actualizar registros
            updated = self.update_demographic_data(account_id, fecha, breakdown, insights)
            
            logger.info(f"   ✅ Actualizados {updated} registros con {breakdown}")
            
            results['breakdowns'][breakdown] = {
                'insights': len(insights),
                'updated': updated
            }
        
        return results


def sync_all_accounts_demographics(
    fecha: Optional[date] = None,
    breakdowns: Optional[List[str]] = None
) -> Dict:
    """
    Sincroniza datos demográficos para todas las cuentas activas.
    
    Args:
        fecha: Fecha a sincronizar (por defecto: ayer)
        breakdowns: Breakdowns a sincronizar
        
    Returns:
        Dict con resultados agregados
    """
    from datetime import timedelta
    
    if fecha is None:
        fecha = date.today() - timedelta(days=1)
    
    logger.info(f"🚀 Iniciando sincronización demográfica para todas las cuentas - {fecha}")
    
    service = MetaAdsDemographicSyncService()
    
    # Obtener cuentas activas
    supabase = create_client_from_env()
    response = supabase.table('meta_ads_cuentas') \
        .select('id_cuenta_publicitaria') \
        .eq('activo', True) \
        .execute()
    
    cuentas = response.data or []
    logger.info(f"📊 Procesando {len(cuentas)} cuentas activas")
    
    resultados = []
    errores = []
    
    for cuenta in cuentas:
        account_id = cuenta['id_cuenta_publicitaria']
        
        try:
            result = service.sync_account_demographics(account_id, fecha, breakdowns)
            resultados.append(result)
            
        except Exception as e:
            error_msg = f"Error en cuenta {account_id}: {e}"
            logger.error(error_msg)
            errores.append(error_msg)
    
    return {
        'ok': True,
        'fecha': fecha.isoformat(),
        'total_cuentas': len(cuentas),
        'exitosas': len(resultados),
        'errores': len(errores),
        'resultados': resultados
    }
