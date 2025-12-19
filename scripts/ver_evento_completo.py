"""Ver TODOS los campos de los eventos sin título"""
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

# IDs de eventos sin título
event_ids = [
    '5go8klv9tfjnp8kui5116lglto',  # 10:00
    '72d1n5ck4vkldk54tofpnu6a01'   # 17:00
]

print(f"Calendario: {calendar_id}\n")

for event_id in event_ids:
    print(f"\n{'='*100}")
    print(f"EVENTO COMPLETO: {event_id}")
    print('='*100)
    
    try:
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        # Imprimir TODO el JSON
        print(json.dumps(event, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}")
