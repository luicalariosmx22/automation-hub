import sys
sys.path.insert(0, 'c:\\Users\\luica\\OneDrive\\Desktop\\automation-hub\\src')

from datetime import date
from automation_hub.integrations.meta_ads.daily_sync_service import MetaAdsDailySyncService
import json

service = MetaAdsDailySyncService()
account_id = '482291961841607'
fecha = date(2025, 12, 18)

# Obtener un insight y procesarlo
result = service.sync_account_daily(account_id, fecha)
print(f"Resultado: {result}")

# Ahora verificar lo que se guardó
db_result = service.supabase.table('meta_ads_anuncios_daily') \
    .select('*') \
    .eq('id_cuenta_publicitaria', account_id) \
    .eq('fecha_reporte', fecha.isoformat()) \
    .limit(1) \
    .execute()

if db_result.data:
    row = db_result.data[0]
    print(f"\n📊 DATOS GUARDADOS:")
    print(f"impresiones: {row.get('impresiones')}")
    print(f"alcance: {row.get('alcance')}")
    print(f"clicks: {row.get('clicks')}")
    print(f"link_clicks: {row.get('link_clicks')}")
    print(f"inline_link_clicks: {row.get('inline_link_clicks')}")
    print(f"interacciones: {row.get('interacciones')}")
    print(f"page_engagement: {row.get('page_engagement')}")
    print(f"post_engagement: {row.get('post_engagement')}")
    print(f"video_views: {row.get('video_views')}")
    print(f"post_reactions: {row.get('post_reactions')}")
    print(f"landing_page_views: {row.get('landing_page_views')}")
    print(f"messaging_conversations_started: {row.get('messaging_conversations_started')}")
