"""
Script para analizar qué columnas de meta_ads_anuncios_daily tienen datos
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Agregar root al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Cargar .env
load_dotenv(root_dir / '.env')

from src.automation_hub.db.supabase_client import create_client_from_env

def analizar_columnas():
    """Analiza qué columnas tienen datos y cuáles no"""
    
    supabase = create_client_from_env()
    
    # Obtener una muestra de datos recientes
    response = supabase.table('meta_ads_anuncios_daily') \
        .select('*') \
        .eq('fecha_reporte', '2025-12-18') \
        .limit(100) \
        .execute()
    
    if not response.data:
        print("❌ No se encontraron datos")
        return
    
    print(f"\n📊 Analizando {len(response.data)} registros del 2025-12-18\n")
    print("=" * 100)
    
    # Analizar cada columna
    columnas_con_datos = {}
    columnas_sin_datos = []
    columnas_siempre_cero = []
    
    # Tomar todas las columnas del primer registro
    columnas = list(response.data[0].keys())
    
    for col in sorted(columnas):
        valores = []
        tiene_datos = False
        solo_ceros = True
        
        for row in response.data:
            val = row.get(col)
            valores.append(val)
            
            # Verificar si tiene datos
            if val is not None and val != '' and val != [] and val != {}:
                tiene_datos = True
                
                # Verificar si no es solo ceros
                if isinstance(val, (int, float)):
                    if val != 0:
                        solo_ceros = False
                else:
                    solo_ceros = False
        
        # Clasificar columna
        if not tiene_datos:
            columnas_sin_datos.append(col)
        elif solo_ceros and isinstance(response.data[0].get(col), (int, float)):
            columnas_siempre_cero.append(col)
        else:
            # Obtener valores únicos (máximo 5)
            valores_unicos = set(str(v)[:50] for v in valores if v is not None and v != 0 and v != '' and v != [] and v != {})
            valores_muestra = list(valores_unicos)[:5]
            columnas_con_datos[col] = {
                'tipo': type(response.data[0].get(col)).__name__,
                'muestra': valores_muestra,
                'count_not_null': sum(1 for v in valores if v is not None and v != 0 and v != '' and v != [] and v != {})
            }
    
    # Mostrar resultados
    print("\n✅ COLUMNAS CON DATOS ({})".format(len(columnas_con_datos)))
    print("=" * 100)
    for col, info in sorted(columnas_con_datos.items()):
        muestra_str = ', '.join(str(v) for v in info['muestra'][:3])
        if len(info['muestra']) > 3:
            muestra_str += '...'
        print(f"  {col:40} ({info['tipo']:15}) - {info['count_not_null']:3} registros - Ej: {muestra_str}")
    
    print("\n⚠️  COLUMNAS SIEMPRE EN CERO ({})".format(len(columnas_siempre_cero)))
    print("=" * 100)
    for col in sorted(columnas_siempre_cero):
        print(f"  - {col}")
    
    print("\n❌ COLUMNAS SIN DATOS / NULL ({})".format(len(columnas_sin_datos)))
    print("=" * 100)
    for col in sorted(columnas_sin_datos):
        print(f"  - {col}")
    
    print("\n" + "=" * 100)
    print(f"\n📊 RESUMEN:")
    print(f"  Total columnas: {len(columnas)}")
    print(f"  ✅ Con datos: {len(columnas_con_datos)}")
    print(f"  ⚠️  Siempre cero: {len(columnas_siempre_cero)}")
    print(f"  ❌ Sin datos: {len(columnas_sin_datos)}")
    print(f"  📈 Porcentaje utilizado: {len(columnas_con_datos) / len(columnas) * 100:.1f}%")
    print()

if __name__ == "__main__":
    analizar_columnas()
