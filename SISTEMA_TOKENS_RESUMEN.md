# 📊 Sistema de Monitoreo y Renovación de Tokens - Resumen Ejecutivo

## ✅ ¿Qué se implementó?

### 1. **Health Check Automático** (15 servicios)
- ✅ OpenAI, DeepSeek, Gemini
- ✅ Google OAuth (GBP y Calendar)
- ✅ Meta/Facebook (API, App, Webhook)
- ✅ Twilio WhatsApp
- ✅ Telegram Bot
- ✅ Supabase
- ✅ TikTok API
- ✅ SMTP Gmail
- ✅ Railway
- ✅ Encryption Keys

**Frecuencia:** 2 veces al día (8 AM y 8 PM)  
**Notificaciones:** Solo cuando algo falla (Telegram)

### 2. **Sistema de Renovación de Tokens con 1 Clic**
- Servidor local en `http://127.0.0.1:5555`
- URLs de renovación directas:
  - GBP: `/renew/gbp`
  - Calendar: `/renew/calendar`
- **Actualización automática del `.env`** - Sin edición manual
- **Links incluidos en notificaciones** - Renovar desde Telegram

### 3. **Tracking de Antigüedad de Tokens** 🆕
- Registro de todas las renovaciones en `.token_renewals.json`
- **Muestra cuántos días tiene cada token**
- **Historial completo** de renovaciones (últimas 100)
- **Estadísticas de duración** para detectar patrones

## 🎯 Cómo Funciona (Flujo Completo)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Job corre automáticamente (8 AM y 8 PM)                 │
│    └─ Verifica 15 servicios                                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Detecta token expirado                                   │
│    • Google OAuth (GBP): Token expirado (7 días)            │
│    • Envía notificación a Telegram                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Notificación incluye:                                    │
│    ❌ Google OAuth (GBP): Token expirado (7 días)           │
│    Renovar: http://127.0.0.1:5555/renew/gbp                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Usuario hace clic en el link                             │
│    └─ Se abre navegador                                     │
│    └─ Redirige a Google OAuth                               │
│    └─ Usuario autoriza (5 segundos)                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Sistema actualiza automáticamente                        │
│    ✅ GBP_REFRESH_TOKEN actualizado en .env                 │
│    ✅ Renovación registrada en .token_renewals.json         │
│    ✅ Timestamp: 2025-12-30 14:45:00                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Próxima verificación (8 PM)                              │
│    ✅ Google OAuth (GBP): OK (renovado hoy)                 │
│    └─ No envía notificación (todo OK)                       │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Archivos Creados

### Principales:
- `src/automation_hub/jobs/api_health_check.py` - Verificación de 15 servicios
- `src/automation_hub/jobs/token_renewal_server.py` - Servidor de renovación
- `.token_renewals.json` - Historial de renovaciones

### Scripts de Utilidad:
- `renovar_tokens.py` - Iniciar servidor de renovación
- `verificar_apis.py` - Ejecutar health check manualmente
- `ver_historial_tokens.py` - Ver historial y estadísticas
- `diagnosticar_google_oauth.py` - Debug de tokens Google

### Documentación:
- `TOKEN_RENEWAL_GUIDE.md` - Guía completa del sistema
- `API_HEALTH_CHECK.md` - Docs del health check
- `API_HEALTH_CHECK_SETUP.md` - Instrucciones de setup

### Configuración:
- `migrations/add_api_health_check_job.sql` - Job en Supabase
- `.gitignore` - Actualizado para excluir `.token_renewals.json`

## 🚀 Comandos Principales

```bash
# Iniciar servidor de renovación
python renovar_tokens.py

# Verificar todas las APIs manualmente
python verificar_apis.py

# Ver historial de renovaciones
python ver_historial_tokens.py

# Ver estadísticas de duración de tokens
python ver_historial_tokens.py --stats

# Debug de tokens Google
python diagnosticar_google_oauth.py
```

## 📊 Estado Actual

### Servicios Funcionando (12/15):
- ✅ OpenAI API
- ✅ DeepSeek API
- ✅ Gemini API
- ✅ Meta/Facebook API
- ✅ Meta App Config
- ✅ Meta Webhook Config
- ✅ Telegram Bot
- ✅ Supabase
- ✅ TikTok API
- ✅ SMTP Gmail
- ✅ Railway Config
- ✅ Encryption Key

### Servicios con Problemas (3/15):
- ❌ **Twilio WhatsApp** - Credenciales REDACTED (esperado)
- ❌ **Google OAuth (GBP)** - Token expirado → http://127.0.0.1:5555/renew/gbp
- ❌ **Google Calendar** - Token expirado → http://127.0.0.1:5555/renew/calendar

## 🔧 Próximos Pasos

### Paso 1: Configurar Google Cloud Console
1. Ve a https://console.cloud.google.com/
2. **APIs & Services** → **Credentials**
3. Agrega estas **Authorized redirect URIs**:
   ```
   http://127.0.0.1:5555/oauth/gbp/callback
   http://127.0.0.1:5555/oauth/calendar/callback
   ```

### Paso 2: Renovar Tokens Expirados
1. Inicia el servidor: `python renovar_tokens.py`
2. Abre http://127.0.0.1:5555/renew/gbp
3. Autoriza en Google
4. Repite para Calendar: http://127.0.0.1:5555/renew/calendar

### Paso 3: Publicar App en Production (Google Cloud)
1. **OAuth consent screen** → **PUBLISH APP**
2. Una vez en "Production", los tokens **NO expirarán cada 7 días**
3. Los refresh tokens durarán indefinidamente

### Paso 4: Aplicar Migración en Supabase
```bash
# Ejecutar en Supabase SQL Editor:
migrations/add_api_health_check_job.sql
```

Esto configura el job para correr automáticamente a las 8 AM y 8 PM.

## 💡 Casos de Uso

### 1. Token expira
- ✅ Recibes notificación en Telegram
- ✅ Haces clic en el link
- ✅ Autorizas en Google
- ✅ Token se renueva automáticamente
- ✅ Siguiente verificación confirma que funciona

### 2. Monitorear duración de tokens
- ✅ `python ver_historial_tokens.py`
- ✅ Ves cuántos días duran los tokens
- ✅ Detectas si están en modo Testing (7 días) o Production (permanente)

### 3. Auditoría de renovaciones
- ✅ `.token_renewals.json` mantiene historial completo
- ✅ Puedes ver quién renovó, cuándo y qué token
- ✅ Estadísticas de frecuencia de renovaciones

## 🎉 Beneficios

✅ **Cero downtime** - Tokens se renuevan sin afectar servicios  
✅ **Notificaciones proactivas** - Te enteras antes de que algo falle  
✅ **Renovación simple** - 1 clic, sin editar archivos  
✅ **Historial completo** - Saber cuándo y cuántas veces se renovó  
✅ **Estadísticas útiles** - Detectar patrones de expiración  
✅ **Automatizado** - Health check corre solo, sin intervención  

## 🔐 Seguridad

- ✅ Servidor solo en `localhost` (127.0.0.1)
- ✅ `.token_renewals.json` excluido de Git
- ✅ Tokens nunca se exponen en logs completos
- ✅ Historial muestra solo preview de tokens (30 chars)
- ✅ Notificaciones Telegram con bot específico (no default)

## 📞 Soporte

Si algo falla:
1. Revisa `TOKEN_RENEWAL_GUIDE.md` para troubleshooting
2. Ejecuta `python diagnosticar_google_oauth.py` para debug
3. Verifica historial con `python ver_historial_tokens.py`
