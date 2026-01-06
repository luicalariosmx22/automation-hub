from dotenv import load_dotenv
import os, sys
load_dotenv('../.env')
sys.path.insert(0, '../src')

from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()
reglas = supabase.table('meta_comentarios_reglas').select('*').eq('activa', True).execute()

if reglas.data:
    regla = reglas.data[0]
    print('REGLA ACTIVA:')
    print('ID:', regla.get('id'))
    print('Nombre:', regla.get('nombre'))
    print('Palabras clave:', regla.get('palabras_clave'))
    print('Acción:', regla.get('accion'))
    print('Parámetros:', regla.get('parametros'))
    print('\nTodos los campos:', regla)
else:
    print('No hay reglas activas')