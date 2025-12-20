#!/usr/bin/env python3
"""
Script de prueba para Meta Ads Daily Sync

Este script permite probar la funcionalidad de sincronización diaria
de Meta Ads usando la nueva tabla meta_ads_anuncios_daily.
"""

import os
import sys
import argparse
from datetime import datetime, date, timedelta
from typing import Optional

# Add project root to path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from automation_hub.integrations.meta_ads.daily_sync_service import MetaAdsDailySyncService


def test_list_accounts():
    """Prueba listar cuentas activas"""
    print("🚀 META ADS DAILY SYNC - SCRIPT DE PRUEBA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("🧪 PRUEBA: Listar cuentas activas")
    print("="*80)
    
    try:
        service = MetaAdsDailySyncService()
        accounts = service.get_active_accounts()
        
        if accounts:
            print(f"📊 Cuentas encontradas: {len(accounts)}")
            for account in accounts:
                nombre = service.clean_surrogates(account.get('nombre_cliente', 'Sin nombre'))
                estado = account.get('estado_actual', 'NULL')
                nora = account.get('nombre_nora', 'Sin Nora')
                print(f"   • {nombre} ({account['id_cuenta_publicitaria']}) - Estado: {estado} - Nora: {nora}")
        else:
            print("❌ No se encontraron cuentas activas")
            return False
            
        print("="*80)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_sync_account_daily(account_id: str, fecha: date, nombre_nora: Optional[str] = None):
    """Prueba sincronización de cuenta individual para fecha específica"""
    print("🚀 META ADS DAILY SYNC - SCRIPT DE PRUEBA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("🧪 PRUEBA: Sincronización diaria de cuenta individual")
    print(f"📊 Cuenta: {account_id}")
    print(f"📅 Fecha: {fecha}")
    print(f"🏷️ Nora: {nombre_nora or 'Todas'}")
    print("="*80)
    
    try:
        service = MetaAdsDailySyncService()
        
        result = service.sync_account_daily(
            account_id=account_id,
            fecha_reporte=fecha,
            nombre_nora=nombre_nora
        )
        
        print(f"\n📋 RESULTADOS:")
        print(f"✅ Éxito: {result.get('ok')}")
        print(f"📊 Anuncios procesados: {result.get('processed', 0)}")
        
        if result.get('errors'):
            print(f"❌ Errores: {len(result['errors'])}")
            for error in result['errors']:
                print(f"   • {error}")
        
        print("="*80)
        if result.get('ok'):
            print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        else:
            print("❌ PRUEBA FALLÓ")
        print("="*80)
        
        return result.get('ok', False)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_sync_all_daily(fecha: date, nombre_nora: Optional[str] = None):
    """Prueba sincronización de todas las cuentas para fecha específica"""
    print("🚀 META ADS DAILY SYNC - SCRIPT DE PRUEBA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("🧪 PRUEBA: Sincronización diaria de todas las cuentas")
    print(f"📅 Fecha: {fecha}")
    print(f"🏷️ Nora: {nombre_nora or 'Todas'}")
    print("="*80)
    
    try:
        service = MetaAdsDailySyncService()
        
        result = service.sync_all_accounts_daily(
            fecha_reporte=fecha,
            nombre_nora=nombre_nora
        )
        
        print(f"\n📋 RESULTADOS FINALES:")
        print(f"✅ Éxito general: {result.get('ok')}")
        print(f"📊 Cuentas procesadas: {result.get('cuentas_procesadas', 0)}")
        print(f"✅ Cuentas exitosas: {result.get('cuentas_exitosas', 0)}")
        print(f"❌ Cuentas con errores: {len(result.get('cuentas_con_errores', []))}")
        
        if result.get('errores'):
            print(f"\n🚨 Errores reportados:")
            for error in result['errores']:
                print(f"   • {error}")
        
        print("="*80)
        if result.get('ok') and result.get('cuentas_exitosas', 0) > 0:
            print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        else:
            print("❌ PRUEBA FALLÓ O SIN RESULTADOS")
        print("="*80)
        
        return result.get('ok', False)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_check_daily_data(account_id: str, fecha: date):
    """Verifica que los datos se guardaron en la tabla daily"""
    print("🚀 META ADS DAILY SYNC - VERIFICACIÓN DE DATOS")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("🧪 PRUEBA: Verificación de datos en tabla daily")
    print(f"📊 Cuenta: {account_id}")
    print(f"📅 Fecha: {fecha}")
    print("="*80)
    
    try:
        service = MetaAdsDailySyncService()
        
        # Query to check data
        result = service.supabase.table('meta_ads_anuncios_daily') \
            .select('ad_id, fecha_reporte, publisher_platform, importe_gastado, impresiones, clicks') \
            .eq('id_cuenta_publicitaria', account_id) \
            .eq('fecha_reporte', fecha.isoformat()) \
            .eq('activo', True) \
            .order('fecha_ultima_actualizacion', desc=True) \
            .limit(5) \
            .execute()
        
        data = result.data
        
        if data:
            print(f"📊 Registros encontrados: {len(data)}")
            print("\n📋 Muestra de datos:")
            for i, row in enumerate(data, 1):
                print(f"{i}. Ad ID: {row['ad_id']}")
                print(f"   Fecha: {row['fecha_reporte']}")
                print(f"   Platform: {row['publisher_platform']}")
                print(f"   Spend: ${row['importe_gastado']}")
                print(f"   Impressions: {row['impresiones']}")
                print(f"   Clicks: {row['clicks']}")
                print()
        else:
            print("❌ No se encontraron datos para la cuenta y fecha especificadas")
            return False
        
        print("="*80)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando datos: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Meta Ads Daily Sync - Script de Prueba')
    parser.add_argument('--list-accounts', action='store_true', help='Listar cuentas activas')
    parser.add_argument('--sync-account', type=str, help='ID de cuenta para sincronizar')
    parser.add_argument('--sync-all', action='store_true', help='Sincronizar todas las cuentas')
    parser.add_argument('--check-data', type=str, help='Verificar datos para cuenta ID')
    parser.add_argument('--date', type=str, help='Fecha específica (YYYY-MM-DD, default: ayer)')
    parser.add_argument('--days-back', type=int, default=1, help='Días hacia atrás desde hoy')
    parser.add_argument('--nora', type=str, help='Filtrar por nombre de Nora')
    
    args = parser.parse_args()
    
    # Determinar fecha
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print("❌ Formato de fecha inválido. Use YYYY-MM-DD")
            return False
    else:
        target_date = date.today() - timedelta(days=args.days_back)
    
    # Ejecutar pruebas
    success = True
    
    if args.list_accounts:
        success = test_list_accounts()
    
    elif args.sync_account:
        success = test_sync_account_daily(args.sync_account, target_date, args.nora)
    
    elif args.sync_all:
        success = test_sync_all_daily(target_date, args.nora)
    
    elif args.check_data:
        success = test_check_daily_data(args.check_data, target_date)
    
    else:
        # Default: listar cuentas
        success = test_list_accounts()
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Error inesperado: {str(e)}")
        sys.exit(1)