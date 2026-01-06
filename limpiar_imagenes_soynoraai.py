#!/usr/bin/env python3
"""
Script para limpiar imágenes de soynoraai.com que están mal
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from automation_hub.db.supabase_client import create_client_from_env

def main():
    supabase = create_client_from_env()
    
    # Primero contar cuántas publicaciones tienen URLs de soynoraai.com
    print("🔍 Buscando publicaciones con URLs de soynoraai.com...")
    
    result = supabase.table("meta_publicaciones_webhook").select("*").like("imagen_local", "%soynoraai.com%").execute()
    
    if not result.data:
        print("✅ No se encontraron URLs de soynoraai.com")
        return
    
    print(f"📊 Encontradas {len(result.data)} publicaciones con URLs de soynoraai.com")
    
    # Mostrar algunos ejemplos
    print("\n📝 Ejemplos de URLs encontradas:")
    for i, pub in enumerate(result.data[:5]):
        print(f"  {i+1}. ID: {pub['id']} - URL: {pub['imagen_local']}")
    
    if len(result.data) > 5:
        print(f"  ... y {len(result.data) - 5} más")
    
    # Confirmar limpieza
    respuesta = input(f"\n❓ ¿Quieres limpiar estas {len(result.data)} URLs? (S/n): ").strip().lower()
    
    if respuesta in ['', 's', 'si', 'sí']:
        print("\n🧹 Limpiando URLs de soynoraai.com...")
        
        # Actualizar para poner imagen_local como NULL
        update_result = supabase.table("meta_publicaciones_webhook").update({
            "imagen_local": None
        }).like("imagen_local", "%soynoraai.com%").execute()
        
        print(f"✅ Limpiadas {len(update_result.data)} publicaciones")
        print("📝 Las URLs de soynoraai.com han sido eliminadas (establecidas como NULL)")
        
        # Verificar que se limpiaron
        verification = supabase.table("meta_publicaciones_webhook").select("*").like("imagen_local", "%soynoraai.com%").execute()
        
        if not verification.data:
            print("✅ Verificación exitosa: No quedan URLs de soynoraai.com")
        else:
            print(f"⚠️ Advertencia: Aún quedan {len(verification.data)} URLs de soynoraai.com")
    else:
        print("❌ Operación cancelada")

if __name__ == "__main__":
    main()