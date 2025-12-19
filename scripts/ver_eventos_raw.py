"""Ver eventos RAW de Google Calendar sin procesamiento"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from automation_hub.integrations.google_calendar.sync_service import GoogleCalendarSyncService
import json
from datetime import datetime, timedelta
import pytz

nombre_nora = "aura"
google_sync = GoogleCalendarSyncService(nombre_nora)

tokens = google_sync._load_tokens()
service = google_sync._build_service(tokens)
calendar_id = tokens.get('google_calendar_id', 'primary')

tz_hermosillo = pytz.timezone('America/Hermosillo')
ahora = datetime.now(tz_hermosillo)

inicio = (ahora - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
fin = (ahora + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)

inicio_utc = inicio.astimezone(pytz.utc)
fin_utc = fin.astimezone(pytz.utc)

print(f"Calendario: {calendar_id}")
print(f"Rango: {inicio.strftime('%Y-%m-%d')} a {fin.strftime('%Y-%m-%d')} (Hermosillo)\n")

events_result = service.events().list(
    calendarId=calendar_id,
    timeMin=inicio_utc.isoformat(),
    timeMax=fin_utc.isoformat(),
    singleEvents=True,
    orderBy='startTime',
    showDeleted=False
).execute()

events = events_result.get('items', [])

print(f"Total eventos: {len(events)}\n")

for i, event in enumerate(events, 1):
    print(f"\n{'='*80}")
    print(f"Evento {i}")
    print('='*80)
    
    # RAW summary field
    summary_raw = event.get('summary')
    print(f"summary (RAW): {repr(summary_raw)}")
    print(f"summary (type): {type(summary_raw)}")
    
    # Start time
    start = event.get('start', {})
    if 'dateTime' in start:
        start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        start_hermosillo = start_dt.astimezone(tz_hermosillo)
        print(f"Inicio: {start_hermosillo.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"Inicio: {start.get('date')} (TODO DIA)")
    
    # Otros campos
    print(f"description: {repr(event.get('description'))}")
    print(f"location: {repr(event.get('location'))}")
    print(f"hangoutLink: {repr(event.get('hangoutLink'))}")
    print(f"Event ID: {event.get('id')}")
