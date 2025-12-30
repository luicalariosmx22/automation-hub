"""
Script para ver el historial de renovaciones de tokens
"""
import json
import os
from datetime import datetime
from pathlib import Path

# Archivo de log
RENEWALS_LOG_FILE = Path(__file__).parent / ".token_renewals.json"

def mostrar_historial():
    """Muestra el historial de renovaciones de tokens"""
    if not RENEWALS_LOG_FILE.exists():
        print("❌ No hay historial de renovaciones todavía")
        print(f"   El archivo {RENEWALS_LOG_FILE} no existe")
        return
    
    with open(RENEWALS_LOG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    renovaciones = data.get("renovaciones", [])
    
    if not renovaciones:
        print("📋 No hay renovaciones registradas")
        return
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  📊 HISTORIAL DE RENOVACIONES DE TOKENS                        ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")
    
    # Agrupar por servicio
    por_servicio = {}
    for renewal in renovaciones:
        servicio = renewal["servicio"]
        if servicio not in por_servicio:
            por_servicio[servicio] = []
        por_servicio[servicio].append(renewal)
    
    # Mostrar resumen por servicio
    print("📈 RESUMEN POR SERVICIO:")
    print("─" * 70)
    
    for servicio, renovs in por_servicio.items():
        exitosas = sum(1 for r in renovs if r["exito"])
        fallidas = len(renovs) - exitosas
        
        if renovs:
            ultima = renovs[-1]
            ultima_fecha = datetime.fromisoformat(ultima["fecha"])
            dias = (datetime.now() - ultima_fecha).days
            
            status = "✅" if ultima["exito"] else "❌"
            
            print(f"\n{status} {servicio}:")
            print(f"   Total renovaciones: {len(renovs)} (✓ {exitosas} | ✗ {fallidas})")
            print(f"   Última renovación: {ultima['fecha_legible']}")
            
            if dias == 0:
                print(f"   Antigüedad: Renovado hoy")
            elif dias == 1:
                print(f"   Antigüedad: 1 día")
            else:
                print(f"   Antigüedad: {dias} días")
            
            if not ultima["exito"]:
                print(f"   ⚠️  Último intento falló: {ultima.get('error', 'Sin detalles')}")
    
    # Mostrar historial completo
    print("\n\n📜 HISTORIAL COMPLETO (últimas 20):")
    print("─" * 70)
    
    for renewal in reversed(renovaciones[-20:]):
        status = "✅" if renewal["exito"] else "❌"
        fecha = renewal["fecha_legible"]
        servicio = renewal["servicio"]
        
        print(f"{status} [{fecha}] {servicio}")
        
        if renewal["exito"] and renewal.get("token_preview"):
            print(f"   Token: {renewal['token_preview']}")
        elif not renewal["exito"] and renewal.get("error"):
            print(f"   Error: {renewal['error']}")
    
    print("\n" + "═" * 70)
    print(f"Total de renovaciones registradas: {len(renovaciones)}")
    print("═" * 70)

def mostrar_estadisticas():
    """Muestra estadísticas de duración de tokens"""
    if not RENEWALS_LOG_FILE.exists():
        print("❌ No hay datos suficientes para estadísticas")
        return
    
    with open(RENEWALS_LOG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    renovaciones = data.get("renovaciones", [])
    
    if len(renovaciones) < 2:
        print("❌ Se necesitan al menos 2 renovaciones para calcular estadísticas")
        return
    
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║  📊 ESTADÍSTICAS DE DURACIÓN DE TOKENS                         ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")
    
    # Calcular duración entre renovaciones del mismo servicio
    por_servicio = {}
    for renewal in renovaciones:
        if renewal["exito"]:
            servicio = renewal["servicio"]
            if servicio not in por_servicio:
                por_servicio[servicio] = []
            por_servicio[servicio].append(renewal)
    
    for servicio, renovs in por_servicio.items():
        if len(renovs) < 2:
            continue
        
        print(f"🔑 {servicio}:")
        
        duraciones = []
        for i in range(1, len(renovs)):
            anterior = datetime.fromisoformat(renovs[i-1]["fecha"])
            actual = datetime.fromisoformat(renovs[i]["fecha"])
            duracion_dias = (actual - anterior).days
            duraciones.append(duracion_dias)
            
            print(f"   • {renovs[i-1]['fecha_legible']} → {renovs[i]['fecha_legible']}: {duracion_dias} días")
        
        if duraciones:
            promedio = sum(duraciones) / len(duraciones)
            print(f"   📈 Duración promedio: {promedio:.1f} días")
            print(f"   ⏱️  Rango: {min(duraciones)} - {max(duraciones)} días")
        
        print()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        mostrar_estadisticas()
    else:
        mostrar_historial()
        
        print("\n💡 Tip: Usa 'python ver_historial_tokens.py --stats' para ver estadísticas de duración")
