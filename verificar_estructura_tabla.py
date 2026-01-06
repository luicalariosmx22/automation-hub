#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla meta_publicaciones_webhook
"""

def main():
    print("🔍 Para ver la estructura de la tabla, ejecuta este SQL:")
    print()
    print("-- Ver columnas de la tabla")
    print("SELECT column_name, data_type, is_nullable")
    print("FROM information_schema.columns")
    print("WHERE table_name = 'meta_publicaciones_webhook'")
    print("ORDER BY ordinal_position;")
    print()
    print("-- Ver algunos registros para entender los campos")
    print("SELECT *")
    print("FROM meta_publicaciones_webhook")
    print("LIMIT 3;")
    print()
    print("-- Buscar campos de fecha")
    print("SELECT column_name")
    print("FROM information_schema.columns")
    print("WHERE table_name = 'meta_publicaciones_webhook'")
    print("  AND (column_name LIKE '%time%' OR column_name LIKE '%date%' OR column_name LIKE '%created%');")

if __name__ == "__main__":
    main()