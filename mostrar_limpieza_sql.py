#!/usr/bin/env python3
"""
Script simplificado para limpiar imágenes de soynoraai.com
"""

def main():
    print("🔍 Para limpiar las URLs de soynoraai.com, ejecuta este SQL:")
    print()
    print("-- Ver cuántas publicaciones tienen URLs de soynoraai.com")
    print("SELECT COUNT(*) FROM meta_publicaciones_webhook WHERE imagen_local LIKE '%soynoraai.com%';")
    print()
    print("-- Ver algunos ejemplos")
    print("SELECT id, page_id, imagen_local FROM meta_publicaciones_webhook WHERE imagen_local LIKE '%soynoraai.com%' LIMIT 5;")
    print()
    print("-- Limpiar todas las URLs de soynoraai.com (establecer como NULL)")
    print("UPDATE meta_publicaciones_webhook SET imagen_local = NULL WHERE imagen_local LIKE '%soynoraai.com%';")
    print()
    print("-- Verificar que se limpiaron")
    print("SELECT COUNT(*) FROM meta_publicaciones_webhook WHERE imagen_local LIKE '%soynoraai.com%';")
    print()
    print("💡 Ejecuta estos comandos en tu cliente SQL de Supabase")

if __name__ == "__main__":
    main()