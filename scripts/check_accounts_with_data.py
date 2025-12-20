#!/usr/bin/env python3
"""
Script temporal para verificar qué cuentas tienen datos de ayer
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from datetime import date, timedelta
from automation_hub.integrations.meta_ads.daily_sync_service import MetaAdsDailySyncService

def main():
    service = MetaAdsDailySyncService()
    accounts = service.get_active_accounts()
    ayer = date.today() - timedelta(days=1)
    
    print(f'🔍 Verificando {len(accounts)} cuentas para fecha: {ayer}')
    print('='*80)
    
    cuentas_con_datos = []
    for i, account in enumerate(accounts[:15], 1):  # Primeras 15 cuentas
        account_id = account['id_cuenta_publicitaria']
        nombre = service.clean_surrogates(account.get('nombre_cliente', 'Sin nombre'))
        
        # Normalizar account_id
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        print(f'{i}. Probando: {nombre[:30]:30} ({account_id})...', end=' ')
        
        try:
            result = service.sync_account_daily(account_id, ayer)
            if result.get('ok') and result.get('anuncios_procesados', 0) > 0:
                anuncios = result['anuncios_procesados']
                print(f'✅ {anuncios} anuncios')
                cuentas_con_datos.append({
                    'id': account_id,
                    'nombre': nombre,
                    'anuncios': anuncios
                })
            else:
                print('⚪ Sin datos')
        except Exception as e:
            error_msg = str(e)[:50]
            print(f'❌ Error: {error_msg}')
    
    print('='*80)
    print(f'📊 Cuentas con datos de ayer: {len(cuentas_con_datos)}')
    if cuentas_con_datos:
        print('\n✅ CUENTAS CON DATOS DISPONIBLES:')
        for cuenta in cuentas_con_datos:
            print(f'  • {cuenta["nombre"]} ({cuenta["id"]}): {cuenta["anuncios"]} anuncios')
    else:
        print('\n⚠️ Ninguna cuenta tiene datos de ayer. Esto puede ser normal si:')
        print('  - Los datos aún no están disponibles en la API de Meta')
        print('  - Las cuentas no tienen anuncios activos')
        print('  - Los anuncios no tuvieron impresiones ese día')

if __name__ == '__main__':
    main()
