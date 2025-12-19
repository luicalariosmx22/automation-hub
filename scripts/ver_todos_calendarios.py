"""Listar TODOS los calendarios disponibles y sus eventos"""
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
print("📅 LISTANDO TODOS LOS CALENDARIOS DISPONIBLES")
print("=" * 80)

nombre_nora = "aura"
google_sync = GoogleCalendarSyncService(nombre_nora)

tokens = google_sync._load_tokens()
service = google_sync._build_service(tokens)

# Listar TODOS los calendarios
print("\n📋 Calendarios disponibles:\n")
calendar_list = service.calendarList().list().execute()

for idx, calendar in enumerate(calendar_list.get('items', []), 1):
    cal_id = calendar['id']
    cal_name = calendar.get('summary', 'Sin nombre')
    primary = ' ⭐ PRIMARY' if calendar.get('primary') else ''
    selected = ' ✅ SELECCIONADO' if cal_id == tokens.get('selected_calendar_id') else ''
    
    print(f"{idx}. {cal_name}{primary}{selected}")
    print(f"   ID: {cal_id}")
    print(f"   Acceso: {calendar.get('accessRole', 'N/A')}")
    print()

print("=" * 80)
print("📅 EVENTOS EN CADA CALENDARIO")
print("=" * 80)

tz_hermosillo = pytz.timezone('America/Hermosillo')
ahora = datetime.now(tz_hermosillo)

# Buscar desde hace 3 días hasta dentro de 7 días
inicio = (ahora - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
fin = (ahora + timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=999999)

inicio_utc = inicio.astimezone(pytz.utc)
fin_utc = fin.astimezone(pytz.utc)

print(f"\nRango de búsqueda: {inicio.strftime('%Y-%m-%d')} a {fin.strftime('%Y-%m-%d')} (Hermosillo)\n")

for idx, calendar in enumerate(calendar_list.get('items', []), 1):
    cal_id = calendar['id']
    cal_name = calendar.get('summary', 'Sin nombre')
    
    print(f"\n{'='*80}")
    print(f"📆 Calendario {idx}: {cal_name}")
    print(f"   ID: {cal_id}")
    print('='*80)
    
    try:
        events_result = service.events().list(
            calendarId=cal_id,
            timeMin=inicio_utc.isoformat(),
            timeMax=fin_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            showDeleted=False
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print("   ❌ Sin eventos en este rango\n")
            continue
        
        print(f"   ✅ {len(events)} eventos encontrados:\n")
        
        for i, event in enumerate(events, 1):
            titulo = event.get('summary', 'Sin título')
            event_id = event.get('id')
            
            # Obtener fecha/hora
            start = event.get('start', {})
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                start_hermosillo = start_dt.astimezone(tz_hermosillo)
                hora_str = start_hermosillo.strftime('%Y-%m-%d %H:%M')
            else:
                start_date = start.get('date')
                hora_str = f"{start_date} (TODO DÍA)"
            
            recurrente = '🔄 ' if 'recurringEventId' in event else ''
            
            print(f"   {i}. {recurrente}{titulo}")
            print(f"      📅 {hora_str}")
            print(f"      🆔 {event_id}")
            
            if event.get('description'):
                desc = event['description'][:80].replace('\n', ' ')
                print(f"      📝 {desc}...")
            print()
    
    except Exception as e:
        print(f"   ❌ Error al consultar calendario: {e}\n")

print("=" * 80)
print("🔍 ¿Cuál calendario debería estar sincronizando?")
print("=" * 80)
