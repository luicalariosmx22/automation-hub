#!/usr/bin/env python3
"""
Script para verificar el formato de las ubicaciones GBP en la base de datos
"""

def main():
    print("🔍 Verificando formato de ubicaciones GBP en base de datos:")
    print()
    print("-- Ver formato actual de location_name en gbp_locations")
    print("SELECT location_name, empresa_id, activa")
    print("FROM gbp_locations")
    print("WHERE activa = true")
    print("LIMIT 10;")
    print()
    print("-- Verificar si tienen formato correcto de Google API")
    print("SELECT ")
    print("  location_name,")
    print("  CASE ")
    print("    WHEN location_name LIKE 'accounts/%/locations/%' THEN 'FORMATO_CORRECTO'")
    print("    WHEN location_name LIKE 'locations/%' THEN 'FALTA_ACCOUNT_ID'")
    print("    ELSE 'FORMATO_INCORRECTO'")
    print("  END as formato")
    print("FROM gbp_locations")
    print("WHERE activa = true;")
    print()
    print("-- Contar por tipo de formato")
    print("SELECT ")
    print("  CASE ")
    print("    WHEN location_name LIKE 'accounts/%/locations/%' THEN 'FORMATO_CORRECTO'")
    print("    WHEN location_name LIKE 'locations/%' THEN 'FALTA_ACCOUNT_ID'")
    print("    ELSE 'FORMATO_INCORRECTO'")
    print("  END as formato,")
    print("  COUNT(*) as total")
    print("FROM gbp_locations")
    print("GROUP BY formato;")
    print()
    print("🚨 PROBLEMA SOSPECHADO:")
    print("   Las ubicaciones pueden estar guardadas como 'locations/12345'")
    print("   Pero Google API necesita 'accounts/ACCOUNT_ID/locations/12345'")
    print("   Si es así, necesitamos el ACCOUNT_ID para construir URLs correctas")

if __name__ == "__main__":
    main()