"""Script para probar la consulta de citas del día"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from datetime import datetime, timezone, timedelta
from automation_hub.db.supabase_client import create_client_from_env
import pytz

print("🔍 Probando consulta de citas del día\n")

supabase = create_client_from_env()
nombre_nora = "aura"

# Obtener TODAS las citas sin filtro de fecha para ver qué hay
print("1️⃣ Consultando TODAS las citas en agenda_citas:")
result_all = supabase.table('agenda_citas') \
    .select('id, titulo, inicio, fin, estado, origen') \
    .eq('nombre_nora', nombre_nora) \
    .order('inicio') \
    .execute()

print(f"   Total citas en BD: {len(result_all.data)}\n")

if result_all.data:
    print("   Primeras 5 citas:")
    for cita in result_all.data[:5]:
        print(f"   - {cita['titulo']}: {cita['inicio']} | Estado: {cita['estado']} | Origen: {cita.get('origen', 'N/A')}")
    print()

# Ahora probar con el rango de hoy (UTC)
print("2️⃣ Probando consulta con rango UTC (como en el job):")
hoy_utc = datetime.now(timezone.utc)
inicio_dia_utc = hoy_utc.replace(hour=0, minute=0, second=0, microsecond=0)
fin_dia_utc = hoy_utc.replace(hour=23, minute=59, second=59, microsecond=999999)

print(f"   Fecha actual UTC: {hoy_utc.isoformat()}")
print(f"   Rango inicio: {inicio_dia_utc.isoformat()}")
print(f"   Rango fin: {fin_dia_utc.isoformat()}\n")

result_utc = supabase.table('agenda_citas') \
    .select('*') \
    .eq('nombre_nora', nombre_nora) \
    .gte('inicio', inicio_dia_utc.isoformat()) \
    .lte('inicio', fin_dia_utc.isoformat()) \
    .neq('estado', 'cancelada') \
    .order('inicio') \
    .execute()

print(f"   Citas encontradas con rango UTC: {len(result_utc.data)}")
if result_utc.data:
    for cita in result_utc.data:
        print(f"   ✅ {cita['titulo']}: {cita['inicio']}")
else:
    print("   ❌ No se encontraron citas")
print()

# Probar con timezone de México
print("3️⃣ Probando consulta con timezone de México:")
tz_mx = pytz.timezone('America/Mexico_City')
hoy_mx = datetime.now(tz_mx)
inicio_dia_mx = hoy_mx.replace(hour=0, minute=0, second=0, microsecond=0)
fin_dia_mx = hoy_mx.replace(hour=23, minute=59, second=59, microsecond=999999)

# Convertir a UTC para la consulta
inicio_dia_mx_utc = inicio_dia_mx.astimezone(timezone.utc)
fin_dia_mx_utc = fin_dia_mx.astimezone(timezone.utc)

print(f"   Fecha actual México: {hoy_mx.isoformat()}")
print(f"   Rango inicio (México): {inicio_dia_mx.isoformat()}")
print(f"   Rango inicio (UTC): {inicio_dia_mx_utc.isoformat()}")
print(f"   Rango fin (México): {fin_dia_mx.isoformat()}")
print(f"   Rango fin (UTC): {fin_dia_mx_utc.isoformat()}\n")

result_mx = supabase.table('agenda_citas') \
    .select('*') \
    .eq('nombre_nora', nombre_nora) \
    .gte('inicio', inicio_dia_mx_utc.isoformat()) \
    .lte('inicio', fin_dia_mx_utc.isoformat()) \
    .neq('estado', 'cancelada') \
    .order('inicio') \
    .execute()

print(f"   Citas encontradas con timezone México: {len(result_mx.data)}")
if result_mx.data:
    for cita in result_mx.data:
        inicio = datetime.fromisoformat(cita['inicio'].replace('Z', '+00:00'))
        inicio_mx = inicio.astimezone(tz_mx)
        print(f"   ✅ {cita['titulo']}")
        print(f"      UTC: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      México: {inicio_mx.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("   ❌ No se encontraron citas")
print()

# Consulta más amplia para ver qué hay cerca
print("4️⃣ Consultando rango de ±2 días para ver qué hay cerca:")
fecha_inicio_amplio = (hoy_utc - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
fecha_fin_amplio = (hoy_utc + timedelta(days=2)).replace(hour=23, minute=59, second=59, microsecond=999999)

result_amplio = supabase.table('agenda_citas') \
    .select('id, titulo, inicio, estado') \
    .eq('nombre_nora', nombre_nora) \
    .gte('inicio', fecha_inicio_amplio.isoformat()) \
    .lte('inicio', fecha_fin_amplio.isoformat()) \
    .neq('estado', 'cancelada') \
    .order('inicio') \
    .execute()

print(f"   Citas en rango de ±2 días: {len(result_amplio.data)}")
if result_amplio.data:
    for cita in result_amplio.data:
        inicio = datetime.fromisoformat(cita['inicio'].replace('Z', '+00:00'))
        inicio_mx = inicio.astimezone(tz_mx)
        print(f"   - {cita['titulo']}: {inicio_mx.strftime('%d/%m/%Y %H:%M')} (México)")
else:
    print("   ❌ No hay citas en ±2 días")

print("\n" + "="*60)
print("📊 Resumen del problema:")
print(f"   Hora actual UTC: {hoy_utc.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Hora actual México: {hoy_mx.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Diferencia: {(hoy_utc.hour - hoy_mx.hour) % 24} horas")
print("\n💡 Recomendación:")
print("   El job debe usar timezone de México para determinar 'hoy'")
print("   pero consultar en UTC (como está almacenado en BD)")
