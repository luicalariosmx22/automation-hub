"""Ver detalles completos de eventos problemáticos"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from automation_hub.integrations.google_calendar.sync_service import GoogleCalendarSyncService
import json

nombre_nora = "aura"
google_sync = GoogleCalendarSyncService(nombre_nora)

tokens = google_sync._load_tokens()
service = google_sync._build_service(tokens)
calendar_id = tokens.get('google_calendar_id', 'primary')

print(f"Consultando eventos problematicos en calendario: {calendar_id}\n")

event_ids = [
    '5go8klv9tfjnp8kui5116lglto',
    '72d1n5ck4vkldk54tofpnu6a01'
]

for event_id in event_ids:
    print(f"\n{'='*80}")
    print(f"Evento ID: {event_id}")
    print('='*80)
    
    try:
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        print(f"\nSummary: '{event.get('summary', 'NO TIENE SUMMARY')}'")
        print(f"Description: '{event.get('description', 'NO TIENE')}'")
        print(f"Start: {event.get('start')}")
        print(f"Status: {event.get('status')}")
        
        print("\n📄 JSON completo:")
        print(json.dumps(event, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error: {e}")
