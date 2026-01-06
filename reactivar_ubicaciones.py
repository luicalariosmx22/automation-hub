#!/usr/bin/env python3
"""
Script para reactivar ubicaciones GBP que fueron marcadas incorrectamente como inactivas
"""

def main():
    print("🔄 REACTIVAR UBICACIONES GBP")
    print()
    print("✅ El arreglo de formato funcionó - ya no hay errores 404 masivos")
    print()
    print("🛠️ Ahora necesitamos reactivar algunas ubicaciones para testing:")
    print()
    print("-- Reactivar todas las ubicaciones (usar con cuidado)")
    print("UPDATE gbp_locations SET activa = true WHERE activa = false;")
    print()
    print("-- O reactivar solo unas pocas para testing:")
    print("UPDATE gbp_locations SET activa = true") 
    print("WHERE activa = false")
    print("  AND location_name IS NOT NULL")
    print("LIMIT 5;")
    print()
    print("-- Ver cuántas se van a reactivar:")
    print("SELECT empresa_id, location_name") 
    print("FROM gbp_locations")
    print("WHERE activa = false")
    print("  AND location_name IS NOT NULL")
    print("LIMIT 10;")
    print()
    print("💡 Recomendación: Reactivar solo 2-3 para probar primero")

if __name__ == "__main__":
    main()