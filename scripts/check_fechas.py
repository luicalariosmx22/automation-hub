"""Verificar qué fechas hay en la BD"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
load_dotenv(root_dir / '.env')

from src.automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

response = supabase.table('meta_ads_anuncios_daily') \
    .select('fecha_reporte,ad_id') \
    .eq('id_cuenta_publicitaria', '482291961841607') \
    .order('fecha_reporte', desc=True) \
    .limit(10) \
    .execute()

print("\nFechas disponibles en BD:")
print("=" * 80)
fechas = {}
for row in response.data:
    fecha = row['fecha_reporte']
    fechas[fecha] = fechas.get(fecha, 0) + 1

for fecha, count in sorted(fechas.items(), reverse=True):
    print(f"  {fecha}: {count} registros")
