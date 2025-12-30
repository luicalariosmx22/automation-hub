"""
Script para iniciar el servidor de renovación de tokens
"""
from src.automation_hub.jobs.token_renewal_server import app, RENEWAL_PORT

if __name__ == '__main__':
    print(f"""
    ╔════════════════════════════════════════════════════════════════╗
    ║  🔄 SERVIDOR DE RENOVACIÓN DE TOKENS GOOGLE OAUTH              ║
    ╚════════════════════════════════════════════════════════════════╝
    
    Servidor iniciado en: http://127.0.0.1:{RENEWAL_PORT}
    
    📍 URLs de Renovación:
    ┌────────────────────────────────────────────────────────────────┐
    │ GBP:      http://127.0.0.1:{RENEWAL_PORT}/renew/gbp            │
    │ Calendar: http://127.0.0.1:{RENEWAL_PORT}/renew/calendar       │
    └────────────────────────────────────────────────────────────────┘
    
    ⚡ Funcionamiento:
    1. Abre la URL en tu navegador
    2. Autoriza el acceso en Google
    3. El .env se actualiza automáticamente
    4. ✅ Listo!
    
    💡 Estas URLs también llegan por Telegram cuando un token expira
    
    Presiona Ctrl+C para detener el servidor
    """)
    
    app.run(host='127.0.0.1', port=RENEWAL_PORT, debug=False, use_reloader=False)
