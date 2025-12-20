#!/usr/bin/env python3
"""
Script de prueba para Meta Ads Sync

Permite probar la sincronización de Meta Ads manualmente con diferentes opciones:
- Sincronizar una cuenta específica
- Sincronizar rango de fechas personalizado
- Generar reportes semanales
- Probar solo una pequeña muestra

Uso:
python scripts/test_meta_ads_sync.py --help
"""

import argparse
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

# Agregar src al path para importar módulos
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from automation_hub.integrations.meta_ads import MetaAdsSyncService, MetaAdsReportsService


def test_sync_account(
    account_id: str,
    fecha_inicio: str,
    fecha_fin: str,
    nombre_nora: str = None
):
    """Prueba sincronización de una cuenta específica"""
    print(f"🧪 PRUEBA: Sincronización de cuenta individual")
    print(f"📊 Cuenta: {account_id}")
    print(f"📅 Período: {fecha_inicio} → {fecha_fin}")
    print(f"🏷️ Nora: {nombre_nora or 'Todas'}")
    print("="*60)
    
    try:
        service = MetaAdsSyncService()
        
        result = service.sync_account(
            account_id=account_id,
            fecha_inicio=date.fromisoformat(fecha_inicio),
            fecha_fin=date.fromisoformat(fecha_fin),
            nombre_nora=nombre_nora
        )
        
        print(f"\\n📋 RESULTADOS:")
        print(f"✅ Éxito: {result.get('ok')}")
        if result.get('ok'):
            print(f"📊 Anuncios procesados: {result.get('processed', 0)}")
            if result.get('errors'):
                print(f"⚠️ Errores: {len(result['errors'])}")
                for error in result['errors'][:3]:  # Solo mostrar primeros 3
                    print(f"   • {error}")
        else:
            print(f"❌ Error: {result.get('error')}")
        
        return result.get('ok', False)
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        return False


def test_sync_all(
    fecha_inicio: str,
    fecha_fin: str,
    nombre_nora: str = None
):
    """Prueba sincronización de todas las cuentas"""
    print(f"🧪 PRUEBA: Sincronización de todas las cuentas")
    print(f"📅 Período: {fecha_inicio} → {fecha_fin}")
    print(f"🏷️ Nora: {nombre_nora or 'Todas'}")
    print("="*60)
    
    try:
        service = MetaAdsSyncService()
        
        result = service.sync_all_accounts(
            nombre_nora=nombre_nora,
            fecha_inicio=date.fromisoformat(fecha_inicio),
            fecha_fin=date.fromisoformat(fecha_fin)
        )
        
        print(f"\\n📋 RESULTADOS:")
        print(f"✅ Éxito: {result.get('ok')}")
        if result.get('ok'):
            print(f"📊 Cuentas procesadas: {result.get('cuentas_procesadas', 0)}")
            print(f"✅ Cuentas exitosas: {result.get('cuentas_exitosas', 0)}")
            print(f"📈 Total ads procesados: {result.get('total_ads_procesados', 0)}")
            if result.get('cuentas_con_errores'):
                print(f"❌ Cuentas con errores: {len(result['cuentas_con_errores'])}")
        else:
            print(f"❌ Error: {result.get('error')}")
        
        return result.get('ok', False)
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        return False


def test_generate_reports(
    fecha_inicio: str,
    fecha_fin: str,
    nombre_nora: str = None
):
    """Prueba generación de reportes semanales"""
    print(f"🧪 PRUEBA: Generación de reportes semanales")
    print(f"📅 Período: {fecha_inicio} → {fecha_fin}")
    print(f"🏷️ Nora: {nombre_nora or 'Todas'}")
    print("="*60)
    
    try:
        service = MetaAdsReportsService()
        
        result = service.generate_weekly_reports(
            nombre_nora=nombre_nora,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        print(f"\\n📋 RESULTADOS:")
        print(f"✅ Éxito: {result.get('ok')}")
        if result.get('ok'):
            print(f"📊 Cuentas procesadas: {result.get('cuentas_procesadas', 0)}")
            print(f"📋 Reportes exitosos: {result.get('reportes_exitosos', 0)}")
            print(f"💰 Gasto total: ${result.get('total_gasto', 0):.2f}")
            print(f"💬 Mensajes totales: {result.get('total_mensajes', 0)}")
            if result.get('reportes_con_errores'):
                print(f"❌ Reportes con errores: {len(result['reportes_con_errores'])}")
        else:
            print(f"❌ Error: {result.get('error')}")
        
        return result.get('ok', False)
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        return False


def list_accounts(nombre_nora: str = None):
    """Lista las cuentas activas disponibles"""
    print(f"📋 CUENTAS ACTIVAS DISPONIBLES")
    print(f"🏷️ Nora: {nombre_nora or 'Todas'}")
    print("="*60)
    
    try:
        service = MetaAdsSyncService()
        cuentas = service.get_active_accounts(nombre_nora)
        
        if not cuentas:
            print("⚠️ No se encontraron cuentas activas")
            return []
        
        print(f"📊 Total: {len(cuentas)} cuentas")
        print()
        
        for i, cuenta in enumerate(cuentas, 1):
            estado = cuenta.get('estado_actual', 'NULL')
            nombre = cuenta.get('nombre_cliente', 'Sin nombre')
            nora = cuenta.get('nombre_nora', 'Sin Nora')
            print(f"{i:2d}. {nombre}")
            print(f"     ID: {cuenta['id_cuenta_publicitaria']}")
            print(f"     Nora: {nora}")
            print(f"     Estado: {estado}")
            print()
        
        return cuentas
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Script de prueba para Meta Ads Sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Listar cuentas disponibles
  python scripts/test_meta_ads_sync.py --list-accounts

  # Sincronizar una cuenta específica (últimos 3 días)
  python scripts/test_meta_ads_sync.py --sync-account act_123456789 --days 3

  # Sincronizar todas las cuentas (ayer)
  python scripts/test_meta_ads_sync.py --sync-all --days 1

  # Sincronizar con fechas específicas
  python scripts/test_meta_ads_sync.py --sync-all --start 2024-12-10 --end 2024-12-15

  # Generar reportes de la semana pasada
  python scripts/test_meta_ads_sync.py --reports --days 7

  # Filtrar por Nora específica
  python scripts/test_meta_ads_sync.py --sync-all --nora "mi_nora" --days 1
        """
    )
    
    parser.add_argument('--list-accounts', action='store_true',
                       help='Listar cuentas activas disponibles')
    
    parser.add_argument('--sync-account', metavar='ACCOUNT_ID',
                       help='Sincronizar cuenta específica')
    
    parser.add_argument('--sync-all', action='store_true',
                       help='Sincronizar todas las cuentas activas')
    
    parser.add_argument('--reports', action='store_true',
                       help='Generar reportes semanales')
    
    parser.add_argument('--start', metavar='YYYY-MM-DD',
                       help='Fecha de inicio (formato: 2024-12-15)')
    
    parser.add_argument('--end', metavar='YYYY-MM-DD',
                       help='Fecha de fin (formato: 2024-12-15)')
    
    parser.add_argument('--days', type=int, metavar='N',
                       help='Sincronizar últimos N días (alternativa a --start/--end)')
    
    parser.add_argument('--nora', metavar='NOMBRE',
                       help='Filtrar por nombre_nora específico')
    
    args = parser.parse_args()
    
    # Validar argumentos
    if not any([args.list_accounts, args.sync_account, args.sync_all, args.reports]):
        parser.error("Debe especificar una acción: --list-accounts, --sync-account, --sync-all, o --reports")
    
    # Calcular fechas
    hoy = date.today()
    
    if args.start and args.end:
        fecha_inicio = args.start
        fecha_fin = args.end
    elif args.days:
        if args.days == 1:
            # 1 día = ayer
            fecha_inicio = fecha_fin = (hoy - timedelta(days=1)).isoformat()
        else:
            # N días = desde hace N días hasta ayer
            fecha_fin = (hoy - timedelta(days=1)).isoformat()
            fecha_inicio = (hoy - timedelta(days=args.days)).isoformat()
    else:
        # Default: ayer
        fecha_inicio = fecha_fin = (hoy - timedelta(days=1)).isoformat()
    
    print(f"🚀 META ADS SYNC - SCRIPT DE PRUEBA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Ejecutar acción
    success = True
    
    if args.list_accounts:
        cuentas = list_accounts(args.nora)
        success = len(cuentas) > 0
    
    elif args.sync_account:
        success = test_sync_account(args.sync_account, fecha_inicio, fecha_fin, args.nora)
    
    elif args.sync_all:
        success = test_sync_all(fecha_inicio, fecha_fin, args.nora)
    
    elif args.reports:
        success = test_generate_reports(fecha_inicio, fecha_fin, args.nora)
    
    # Resultado final
    print("="*80)
    if success:
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
    else:
        print("❌ PRUEBA FALLÓ")
    print("="*80)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()