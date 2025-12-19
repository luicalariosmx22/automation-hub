"""Intentar obtener evento privado con maxAttendees"""
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from automation_hub.integrations.google_calendar.sync_service import GoogleCalendarSyncService

nombre_nora = "aura"
google_sync = GoogleCalendarSyncService(nombre_nora)

tokens = google_sync._load_tokens()
service = google_sync._build_service(tokens)
calendar_id = tokens.get('google_calendar_id')

event_id = '5go8klv9tfjnp8kui5116lglto'

print(f"Probando diferentes parametros para evento privado...\n")

# Intentar con diferentes parámetros
try:
    print("1. Get basico:")
    event = service.events().get(
        calendarId=calendar_id,
        eventId=event_id
    ).execute()
    print(f"   summary: {event.get('summary', 'NO TIENE')}")
    
    print("\n2. Get con maxAttendees:")
    event = service.events().get(
        calendarId=calendar_id,
        eventId=event_id,
        maxAttendees=1
    ).execute()
    print(f"   summary: {event.get('summary', 'NO TIENE')}")
    
    print("\n3. Verificar si eres propietario:")
    cal_info = service.calendars().get(calendarId=calendar_id).execute()
    print(f"   accessRole del calendario: {cal_info.get('accessRole', 'N/A')}")
    
    print("\n4. Verificar creator del evento:")
    print(f"   creator: {event.get('creator', 'N/A')}")
    print(f"   organizer: {event.get('organizer', 'N/A')}")
    
    print("\n5. Verificar si hay extension data:")
    print(f"   extendedProperties: {event.get('extendedProperties', 'NO TIENE')}")
    print(f"   privateCopy: {event.get('privateCopy', 'NO TIENE')}")
    
except Exception as e:
    print(f"Error: {e}")
