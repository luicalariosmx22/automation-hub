"""Ver citas directamente de Google Calendar (sin BD)"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from datetime import datetime, timedelta
import pytz
from automation_hub.integrations.google_calendar.sync_service import GoogleCalendarSyncService

print("=" * 80)
print("📅 CITAS DIRECTAMENTE DE GOOGLE CALENDAR")
print("=" * 80)

nombre_nora = "aura"
google_sync = GoogleCalendarSyncService(nombre_nora)

# Ver status
status = google_sync.get_connection_status()
print(f"\n✅ Conectado: {status.get('connected')}")
print(f"   Calendario: {status.get('calendar_name', 'N/A')}")
print(f"   Email: {status.get('user_email', 'N/A')}")

if not status.get('connected'):
    print("\n❌ No hay conexión con Google Calendar")
    sys.exit(1)

# Buscar citas desde el lunes de esta semana hasta el domingo
tz_hermosillo = pytz.timezone('America/Hermosillo')
ahora = datetime.now(tz_hermosillo)

# Desde hace 3 días hasta dentro de 7 días
inicio = (ahora - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
fin = (ahora + timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=999999)

print(f"\n🔍 Buscando citas desde {inicio.strftime('%Y-%m-%d')} hasta {fin.strftime('%Y-%m-%d')}")
print(f"   Zona horaria: {tz_hermosillo}")

# Convertir a UTC para la API
inicio_utc = inicio.astimezone(pytz.utc)
fin_utc = fin.astimezone(pytz.utc)

# Obtener eventos directamente de Google
import logging
logging.basicConfig(level=logging.INFO)

tokens = google_sync._load_tokens()
service = google_sync._build_service(tokens)
calendar_id = tokens.get('selected_calendar_id', 'primary')

print(f"\n📞 Llamando a Google Calendar API...")
print(f"   Calendar ID: {calendar_id}")
print(f"   Rango UTC: {inicio_utc.isoformat()} a {fin_utc.isoformat()}")

events_result = service.events().list(
    calendarId=calendar_id,
    timeMin=inicio_utc.isoformat(),
    timeMax=fin_utc.isoformat(),
    singleEvents=True,
    orderBy='startTime',
    showDeleted=False
).execute()

events = events_result.get('items', [])

print(f"\n✅ Total de eventos encontrados: {len(events)}\n")
print("=" * 80)

if not events:
    print("❌ No se encontraron eventos en Google Calendar")
else:
    for i, event in enumerate(events, 1):
        titulo = event.get('summary', 'Sin título')
        event_id = event.get('id')
        
        # Obtener fecha/hora
        start = event.get('start', {})
        if 'dateTime' in start:
            # Evento con hora
            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            start_hermosillo = start_dt.astimezone(tz_hermosillo)
            hora_str = start_hermosillo.strftime('%Y-%m-%d %H:%M:%S')
            tipo = "CON HORA"
        else:
            # Evento todo el día
            start_date = start.get('date')
            hora_str = f"{start_date} (TODO EL DÍA)"
            tipo = "TODO DÍA"
        
        print(f"\n{i}. {titulo}")
        print(f"   ID: {event_id}")
        print(f"   Tipo: {tipo}")
        print(f"   Inicio (Hermosillo): {hora_str}")
        print(f"   Estado: {event.get('status', 'N/A')}")
        
        # Verificar si es recurrente
        if 'recurringEventId' in event:
            print(f"   🔄 Instancia de evento recurrente: {event['recurringEventId']}")
        
        # Mostrar descripción si existe
        if event.get('description'):
            desc = event['description'][:100]
            print(f"   📝 Descripción: {desc}...")

print("\n" + "=" * 80)
print(f"📊 RESUMEN: {len(events)} eventos en Google Calendar")
print("=" * 80)
