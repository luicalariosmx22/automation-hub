#!/usr/bin/env python3
"""Script para ver los datos reales de facebook_paginas."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from automation_hub.db.supabase_client import create_client_from_env

def main():
    supabase = create_client_from_env()
    
    result = supabase.table('facebook_paginas').select('page_id, nombre_pagina, empresa, nombre_cliente, nombre_nora').limit(5).execute()
    
    print("=== DATOS DE FACEBOOK_PAGINAS ===")
    for pagina in result.data:
        print(f"Page ID: {pagina['page_id']}")
        print(f"Nombre: {pagina['nombre_pagina']}")
        print(f"Empresa: {pagina['empresa']}")
        print(f"Nombre Cliente: {pagina['nombre_cliente']}")
        print(f"Nombre Nora: {pagina['nombre_nora']}")
        print("---")

if __name__ == '__main__':
    main()