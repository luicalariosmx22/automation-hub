#!/usr/bin/env python3
"""
Script para verificar y corregir formato de ubicaciones GBP
"""

def main():
    print("🔍 PROBLEMA IDENTIFICADO: Formato de location_name incorrecto")
    print()
    print("📚 La documentación oficial de Google muestra:")
    print("   ✅ URL correcta: POST https://mybusiness.googleapis.com/v4/accounts/{accountId}/locations/{locationId}/localPosts")
    print("   ❌ URL que usamos: POST https://mybusiness.googleapis.com/v4/locations/{locationId}/localPosts")
    print()
    print("🛠️ SOLUCIÓN: Necesitamos el account ID completo")
    print()
    print("1️⃣ Primero, verifica el formato actual:")
    print()
    print("-- Ver formatos actuales en gbp_locations")
    print("SELECT location_name, CASE")
    print("  WHEN location_name LIKE 'accounts/%/locations/%' THEN 'CORRECTO'")
    print("  WHEN location_name LIKE 'locations/%' THEN 'FALTA_ACCOUNT'")
    print("  ELSE 'OTRO'")
    print("END as formato, COUNT(*)")
    print("FROM gbp_locations")
    print("GROUP BY formato;")
    print()
    print("2️⃣ Si están en formato 'locations/XXXXX', necesitamos:")
    print("   - Obtener el account ID de Google")
    print("   - Actualizar todas las ubicaciones al formato completo")
    print()
    print("💡 El script actualizar_ubicaciones_gbp.py puede obtener el account ID correcto")

if __name__ == "__main__":
    main()