"""
Helper para migrar datos desde meta_ads_anuncios_detalle a meta_ads_anuncios_daily

Este script permite migrar datos existentes de rangos de fechas a registros diarios individuales.
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.automation_hub.core.db import create_client_from_env


class MetaAdsMigrationHelper:
    """Helper para migrar datos entre tablas de Meta Ads"""
    
    def __init__(self):
        self.supabase = create_client_from_env()
    
    def get_date_range_data(
        self, 
        start_date: date, 
        end_date: date,
        account_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtiene datos de meta_ads_anuncios_detalle para un rango de fechas
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            account_id: ID de cuenta específica (opcional)
            
        Returns:
            Lista de registros de meta_ads_anuncios_detalle
        """
        query = self.supabase.table('meta_ads_anuncios_detalle') \
            .select('*') \
            .gte('fecha_inicio', start_date.isoformat()) \
            .lte('fecha_fin', end_date.isoformat()) \
            .eq('activo', True)
        
        if account_id:
            query = query.eq('id_cuenta_publicitaria', account_id)
        
        result = query.execute()
        return result.data or []
    
    def convert_range_to_daily_records(self, range_record: Dict) -> List[Dict]:
        """
        Convierte un registro de rango de fechas a múltiples registros diarios
        
        Args:
            range_record: Registro de meta_ads_anuncios_detalle
            
        Returns:
            Lista de registros para meta_ads_anuncios_daily
        """
        try:
            # Parse dates
            start_date = datetime.strptime(range_record['fecha_inicio'], '%Y-%m-%d').date()
            end_date = datetime.strptime(range_record['fecha_fin'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            print(f"❌ Error parseando fechas para ad {range_record.get('ad_id', 'unknown')}")
            return []
        
        # Calcular días en el rango
        days_in_range = (end_date - start_date).days + 1
        
        if days_in_range <= 0:
            print(f"❌ Rango de fechas inválido para ad {range_record.get('ad_id', 'unknown')}")
            return []
        
        daily_records = []
        current_date = start_date
        
        while current_date <= end_date:
            # Crear registro diario dividiendo métricas entre días
            daily_record = {
                # Identificadores (iguales)
                'ad_id': range_record['ad_id'],
                'id_cuenta_publicitaria': range_record['id_cuenta_publicitaria'],
                'campana_id': range_record.get('campana_id'),
                'conjunto_id': range_record.get('conjunto_id'),
                
                # Fechas específicas para daily
                'fecha_reporte': current_date.isoformat(),
                'fecha_desde': range_record.get('fecha_inicio'),
                'fecha_hasta': range_record.get('fecha_fin'),
                
                # Metadata
                'nombre_anuncio': range_record.get('nombre_anuncio'),
                'nombre_campana': range_record.get('nombre_campana'),
                'nombre_conjunto': range_record.get('nombre_conjunto'),
                'publisher_platform': range_record['publisher_platform'],
                'objetivo_campana': range_record.get('objetivo_campana'),
                'status_campana': range_record.get('status_campana'),
                'status_conjunto': range_record.get('status_conjunto'),
                'status': range_record.get('status'),
                'nombre_nora': range_record['nombre_nora'],
                
                # Métricas divididas por días (distribución uniforme)
                'importe_gastado': self._divide_metric(range_record.get('importe_gastado'), days_in_range),
                'impresiones': self._divide_metric(range_record.get('impresiones'), days_in_range, as_int=True),
                'alcance': self._divide_metric(range_record.get('alcance'), days_in_range, as_int=True),
                'clicks': self._divide_metric(range_record.get('clicks'), days_in_range, as_int=True),
                'link_clicks': self._divide_metric(range_record.get('link_clicks'), days_in_range, as_int=True),
                'inline_link_clicks': self._divide_metric(range_record.get('inline_link_clicks'), days_in_range, as_int=True),
                
                # Métricas de ratio (mantener iguales)
                'ctr': range_record.get('ctr'),
                'cpc': range_record.get('cpc'),
                'cost_per_1k_impressions': range_record.get('cost_per_1k_impressions'),
                'frequency': range_record.get('frequency'),
                'unique_ctr': range_record.get('unique_ctr'),
                
                # Métricas unique (dividir)
                'unique_clicks': self._divide_metric(range_record.get('unique_clicks'), days_in_range, as_int=True),
                'unique_inline_link_clicks': self._divide_metric(range_record.get('unique_inline_link_clicks'), days_in_range, as_int=True),
                'unique_impressions': self._divide_metric(range_record.get('unique_impressions'), days_in_range, as_int=True),
                
                # Video métricas (dividir)
                'video_plays': self._divide_metric(range_record.get('video_plays'), days_in_range, as_int=True),
                'video_plays_at_25': self._divide_metric(range_record.get('video_plays_at_25'), days_in_range, as_int=True),
                'video_plays_at_50': self._divide_metric(range_record.get('video_plays_at_50'), days_in_range, as_int=True),
                'video_plays_at_75': self._divide_metric(range_record.get('video_plays_at_75'), days_in_range, as_int=True),
                'video_plays_at_100': self._divide_metric(range_record.get('video_plays_at_100'), days_in_range, as_int=True),
                'thruplays': self._divide_metric(range_record.get('thruplays'), days_in_range, as_int=True),
                
                # Messaging (dividir)
                'messaging_conversations_started': self._divide_metric(range_record.get('messaging_conversations_started'), days_in_range, as_int=True),
                'messaging_first_reply': self._divide_metric(range_record.get('messaging_first_reply'), days_in_range, as_int=True),
                'mensajes_total': self._divide_metric(range_record.get('mensajes_total'), days_in_range, as_int=True),
                
                # Engagement (dividir)
                'post_engagement': self._divide_metric(range_record.get('post_engagement'), days_in_range, as_int=True),
                'page_engagement': self._divide_metric(range_record.get('page_engagement'), days_in_range, as_int=True),
                'unique_outbound_clicks': self._divide_metric(range_record.get('unique_outbound_clicks'), days_in_range, as_int=True),
                
                # Costos (mantener iguales - son ratios)
                'cost_per_messaging_conversation_started': range_record.get('cost_per_messaging_conversation_started'),
                'cost_per_message': range_record.get('cost_per_message'),
                'cost_per_messaging_first_reply': range_record.get('cost_per_messaging_first_reply'),
                'costo_por_mensaje_total': range_record.get('costo_por_mensaje_total'),
                
                # Flags y metadata
                'msg_cost_is_calculated': range_record.get('msg_cost_is_calculated', False),
                'messages_source': range_record.get('messages_source'),
                'activo': True,
                'fecha_sincronizacion': datetime.utcnow().isoformat(),
                'fecha_ultima_actualizacion': datetime.utcnow().isoformat()
            }
            
            daily_records.append(daily_record)
            current_date += timedelta(days=1)
        
        return daily_records
    
    def _divide_metric(self, value, days: int, as_int: bool = False):
        """Divide una métrica entre el número de días"""
        if value is None or value == 0:
            return 0
        
        try:
            divided = float(value) / days
            return int(divided) if as_int else round(divided, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return 0
    
    def migrate_date_range(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[str] = None,
        batch_size: int = 100
    ) -> Dict:
        """
        Migra datos de un rango de fechas desde detalle a daily
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            account_id: Cuenta específica (opcional)
            batch_size: Tamaño del lote para inserción
            
        Returns:
            Dict con resultados de la migración
        """
        print(f"🔄 Iniciando migración: {start_date} → {end_date}")
        if account_id:
            print(f"📊 Cuenta específica: {account_id}")
        
        try:
            # Obtener datos de rango
            range_data = self.get_date_range_data(start_date, end_date, account_id)
            
            if not range_data:
                print(f"ℹ️ No se encontraron datos para migrar en el rango especificado")
                return {'ok': True, 'migrated': 0, 'errors': []}
            
            print(f"📊 Registros de rango encontrados: {len(range_data)}")
            
            # Convertir a registros diarios
            all_daily_records = []
            conversion_errors = []
            
            for range_record in range_data:
                try:
                    daily_records = self.convert_range_to_daily_records(range_record)
                    all_daily_records.extend(daily_records)
                except Exception as e:
                    error_msg = f"Error convirtiendo ad {range_record.get('ad_id')}: {str(e)}"
                    conversion_errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            print(f"📊 Registros diarios generados: {len(all_daily_records)}")
            
            # Insertar en lotes
            inserted_count = 0
            insert_errors = []
            
            for i in range(0, len(all_daily_records), batch_size):
                batch = all_daily_records[i:i + batch_size]
                try:
                    self.supabase.table('meta_ads_anuncios_daily') \
                        .upsert(batch, on_conflict='ad_id,fecha_reporte,publisher_platform') \
                        .execute()
                    
                    inserted_count += len(batch)
                    print(f"✅ Lote {i//batch_size + 1}: {len(batch)} registros insertados")
                    
                except Exception as e:
                    error_msg = f"Error insertando lote {i//batch_size + 1}: {str(e)}"
                    insert_errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            # Resultados
            all_errors = conversion_errors + insert_errors
            
            print(f"\n📊 MIGRACIÓN COMPLETADA:")
            print(f"✅ Registros migrados: {inserted_count}")
            print(f"❌ Errores: {len(all_errors)}")
            
            return {
                'ok': True,
                'migrated': inserted_count,
                'errors': all_errors,
                'range_records_processed': len(range_data),
                'daily_records_generated': len(all_daily_records)
            }
            
        except Exception as e:
            error_msg = f"Error en migración: {str(e)}"
            print(f"💥 {error_msg}")
            return {'ok': False, 'error': error_msg}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Meta Ads Migration Helper')
    parser.add_argument('--start-date', type=str, required=True, help='Fecha inicio (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True, help='Fecha fin (YYYY-MM-DD)')
    parser.add_argument('--account-id', type=str, help='ID cuenta específica')
    parser.add_argument('--batch-size', type=int, default=100, help='Tamaño del lote')
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        
        helper = MetaAdsMigrationHelper()
        result = helper.migrate_date_range(
            start_date=start_date,
            end_date=end_date,
            account_id=args.account_id,
            batch_size=args.batch_size
        )
        
        if result.get('ok'):
            print(f"\n🎉 Migración exitosa: {result.get('migrated', 0)} registros")
        else:
            print(f"\n💥 Migración falló: {result.get('error', 'Error desconocido')}")
        
        sys.exit(0 if result.get('ok') else 1)
        
    except ValueError as e:
        print(f"❌ Error en formato de fecha: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()