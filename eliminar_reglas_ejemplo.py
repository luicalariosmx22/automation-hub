#!/usr/bin/env python3
"""Script para eliminar reglas de ejemplo."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from automation_hub.db.supabase_client import create_client_from_env

def main():
    supabase = create_client_from_env()
    
    # Eliminar todas las reglas donde nombre_nora='Sistema'
    result = supabase.table('meta_comentarios_reglas').delete().eq('nombre_nora', 'Sistema').execute()
    
    print(f"✅ Eliminadas {len(result.data)} reglas de ejemplo")

if __name__ == '__main__':
    main()