#!/usr/bin/env python3
"""
Script para verificar cuántas publicaciones tenemos de dic 2025 y ene 2026
"""

def main():
    print("🔍 Para verificar publicaciones recientes, ejecuta este SQL:")
    print()
    print("-- Contar publicaciones pendientes de dic 2025 y ene 2026")
    print("SELECT COUNT(*) as total_recientes")
    print("FROM meta_publicaciones_webhook") 
    print("WHERE publicada_gbp = false")
    print("  AND mensaje IS NOT NULL")
    print("  AND creada_en >= '2025-12-01';")
    print()
    print("-- Ver detalles por mes")
    print("SELECT ")
    print("  DATE_TRUNC('month', creada_en) as mes,")
    print("  COUNT(*) as total")
    print("FROM meta_publicaciones_webhook")
    print("WHERE publicada_gbp = false")
    print("  AND mensaje IS NOT NULL")
    print("  AND creada_en >= '2025-12-01'")
    print("GROUP BY DATE_TRUNC('month', creada_en)")
    print("ORDER BY mes DESC;")
    print()
    print("-- Ver algunos ejemplos")
    print("SELECT id, page_id, mensaje, imagen_local, creada_en")
    print("FROM meta_publicaciones_webhook")
    print("WHERE publicada_gbp = false")
    print("  AND mensaje IS NOT NULL")
    print("  AND creada_en >= '2025-12-01'")
    print("ORDER BY creada_en DESC")
    print("LIMIT 5;")

if __name__ == "__main__":
    main()