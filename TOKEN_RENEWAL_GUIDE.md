# 🔄 Sistema de Renovación Automática de Tokens Google OAuth

## 📋 Descripción

Sistema que detecta tokens expirados, permite renovarlos con un solo clic y **registra el historial de renovaciones** para monitorear la duración de los tokens.

## ⚡ Flujo Automático

1. **Health Check detecta token expirado** (corre 2 veces al día)
2. **Envía notificación por Telegram** con link de renovación y antigüedad del token
3. **Usuario hace clic en el link** → Se abre el navegador
4. **Autoriza en Google** (toma 5 segundos)
5. **Sistema actualiza .env automáticamente** ✅
6. **Registra la renovación con timestamp** 📝
7. **Próxima verificación confirma que funciona** y muestra antigüedad ✅

## 📊 Tracking de Antigüedad

El sistema registra cada renovación en `.token_renewals.json` con:
- Servicio (GBP, Calendar)
- Fecha y hora de renovación
- Preview del token renovado
- Estado (éxito/error)

### Ver historial:

```bash
# Ver historial completo
python ver_historial_tokens.py

# Ver estadísticas de duración
python ver_historial_tokens.py --stats
```

## 🚀 Uso Manual

### Iniciar servidor de renovación:

```bash
python renovar_tokens.py
```

El servidor se ejecuta en: `http://127.0.0.1:5555`

### URLs de renovación:

- **GBP (Google Business Profile):** http://127.0.0.1:5555/renew/gbp
- **Google Calendar:** http://127.0.0.1:5555/renew/calendar

## 🔧 Cómo Funciona

### 1. Detección Automática

El job `api.health_check` verifica todos los tokens cada 12 horas (8 AM y 8 PM).

Cuando encuentra un token expirado, envía una notificación como esta:

```
❌ APIs con problemas (3/15):

• Google OAuth (GBP): Token expirado - Renovar: http://127.0.0.1:5555/renew/gbp
• Google Calendar: Token expirado - Renovar: http://127.0.0.1:5555/renew/calendar
```

### 2. Renovación con 1 Clic

1. **Haz clic** en el link de la notificación
2. **Autoriza** en Google (si no estás logueado, te pedirá login)
3. **Listo** - El .env se actualiza automáticamente

### 3. Actualización Automática del .env

El servidor recibe el callback de Google y actualiza:
- `GBP_REFRESH_TOKEN` para Google Business Profile
- `GOOGLE_CALENDAR_REFRESH_TOKEN` para Calendar

**No necesitas editar archivos manualmente** 🎉

## 🛠️ Solución de Problemas

### ❌ "No se obtuvo refresh token"

**Causa:** Google no envió un refresh token porque ya existe uno activo.

**Solución:**
1. Ve a https://myaccount.google.com/permissions
2. Busca tu aplicación ("Soy Nora AI" o similar)
3. Haz clic en "Remove access"
4. Vuelve a abrir el link de renovación

### ⚠️ Tokens siguen expirando cada 7 días

**Causa:** Tu aplicación de Google Cloud está en modo "Testing".

**Solución:**
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Selecciona tu proyecto
3. **APIs & Services** → **OAuth consent screen**
4. Haz clic en **"PUBLISH APP"**
5. Una vez en "Production", los tokens NO expirarán

### 🔒 Error "redirect_uri_mismatch"

**Causa:** La URL de callback no está registrada en Google Cloud.

**Solución:**
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. **APIs & Services** → **Credentials**
3. Selecciona tu OAuth 2.0 Client ID
4. En "Authorized redirect URIs", agrega:
   - `http://127.0.0.1:5555/oauth/gbp/callback`
   - `http://127.0.0.1:5555/oauth/calendar/callback`

## 📡 Integración con Health Check

El health check job incluye automáticamente los links de renovación en las notificaciones:

```python
# src/automation_hub/jobs/api_health_check.py

def verificar_google_oauth() -> Tuple[bool, str]:
    # ...verificación...
    if token_expirado:
        return False, "Token expirado - Renovar: http://127.0.0.1:5555/renew/gbp"
```

## 🎯 Configuración Recomendada

### Para Producción (Railway, Render, etc.):

1. **Publica la app en Google Cloud** (modo Production)
2. **Configura URLs de callback** con tu dominio:
   ```
   https://app.soynoraai.com/oauth/gbp/callback
   https://app.soynoraai.com/oauth/calendar/callback
   ```
3. **Despliega el servidor de renovación** junto con tu app principal

### Para Desarrollo Local:

1. **Mantén las URLs locales** en Google Cloud:
   ```
   http://127.0.0.1:5555/oauth/gbp/callback
   http://127.0.0.1:5555/oauth/calendar/callback
   ```
2. **Inicia el servidor** con `python renovar_tokens.py`
3. **Deja corriendo** mientras trabajas (opcional)

## ✅ Ventajas

✅ **Renovación con 1 clic** - No más edición manual de .env  
✅ **Notificaciones automáticas** - Te enteras cuando algo falla  
✅ **Links directos en Telegram** - Renovar desde el móvil  
✅ **Actualización automática** - El .env se modifica solo  
✅ **Sin downtime** - Renuevas tokens sin reiniciar servicios  
✅ **Historial completo** - Saber cuándo se renovó cada token  
✅ **Tracking de duración** - Monitorear cuánto duran los tokens  
✅ **Estadísticas** - Ver patrones de expiración  

## 📈 Ejemplos de Uso del Historial

### Ver renovaciones recientes:

```bash
python ver_historial_tokens.py
```

Output:
```
╔════════════════════════════════════════════════════════════════╗
║  📊 HISTORIAL DE RENOVACIONES DE TOKENS                        ║
╚════════════════════════════════════════════════════════════════╝

📈 RESUMEN POR SERVICIO:
──────────────────────────────────────────────────────────────────

✅ GBP:
   Total renovaciones: 3 (✓ 3 | ✗ 0)
   Última renovación: 2025-12-30 14:45:00
   Antigüedad: 2 días

✅ Calendar:
   Total renovaciones: 2 (✓ 2 | ✗ 0)
   Última renovación: 2025-12-28 10:30:00
   Antigüedad: 4 días
```

### Ver estadísticas de duración:

```bash
python ver_historial_tokens.py --stats
```

Output:
```
╔════════════════════════════════════════════════════════════════╗
║  📊 ESTADÍSTICAS DE DURACIÓN DE TOKENS                         ║
╚════════════════════════════════════════════════════════════════╝

🔑 GBP:
   • 2025-12-20 10:00:00 → 2025-12-27 14:30:00: 7 días
   • 2025-12-27 14:30:00 → 2025-12-30 14:45:00: 3 días
   📈 Duración promedio: 5.0 días
   ⏱️  Rango: 3 - 7 días

🔑 Calendar:
   • 2025-12-23 09:15:00 → 2025-12-28 10:30:00: 5 días
   📈 Duración promedio: 5.0 días
   ⏱️  Rango: 5 - 5 días
```

**Interpretación:**
- Si los tokens duran ~7 días → App en modo "Testing"
- Si duran meses/años → App en modo "Production" ✅

## 🔐 Seguridad

- El servidor solo corre en `localhost` (127.0.0.1)
- No expone tokens en logs
- Actualiza .env de forma segura usando `python-dotenv`
- Las credenciales nunca salen de tu máquina

## 📝 Ejemplo Completo

```bash
# 1. Iniciar servidor (en una terminal)
python renovar_tokens.py

# 2. En otra terminal, probar el health check
python verificar_apis.py

# 3. Si detecta tokens expirados, verás:
# ❌ Google OAuth (GBP): Token expirado - Renovar: http://127.0.0.1:5555/renew/gbp

# 4. Abrir el link en navegador:
http://127.0.0.1:5555/renew/gbp

# 5. Autorizar en Google

# 6. ✅ .env actualizado automáticamente!

# 7. Verificar de nuevo
python verificar_apis.py
# ✅ Google OAuth (GBP): OK
```

## 🚀 Próximos Pasos

1. **Publica tu app en Google Cloud** para evitar expiración de tokens
2. **Agrega las URLs de callback** a tu configuración de OAuth
3. **Prueba el flujo** renovando un token manualmente
4. **Configura el job de health check** en Supabase para que corra automáticamente
