# 🤖 Configuración de Notificaciones por Telegram

## ¿Por qué Telegram?

- ✅ **100% GRATIS** - Sin límites de mensajes
- ⚡ **Instantáneo** - Notificaciones en tiempo real
- 🔔 **Sonido** - Alertas de alta prioridad con notificación
- 📱 **Multiplataforma** - Desktop, móvil, web
- 🎨 **Rico en formatos** - HTML, botones, archivos
- 👥 **Grupos** - Compartir alertas con el equipo

## Configuración Rápida (5 minutos)

### 1. Crear el Bot

1. Abre Telegram y busca: **@BotFather**
2. Envía: `/newbot`
3. Sigue las instrucciones:
   - Nombre del bot: `Automation Hub Alerts` (o el que prefieras)
   - Username: `tu_empresa_alerts_bot` (debe terminar en `_bot`)
4. **Copia el token** que te da (algo como: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Obtener tu Chat ID

**Opción A - Usando el script helper:**
```bash
python scripts/setup_telegram_bot.py
# Pega tu token cuando te lo pida
# Envía un mensaje a tu bot en Telegram
# Vuelve a ejecutar el script
```

**Opción B - Manual:**
1. Envía un mensaje a tu bot en Telegram (cualquier cosa, ej: "Hola")
2. Abre en el navegador:
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
3. Busca `"chat":{"id":123456789` - ese número es tu **chat_id**

### 3. Configurar las Variables

Agrega a tu archivo `.env`:

```bash
# --- TELEGRAM BOT (Notificaciones) ---
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```

### 4. Probar

```bash
# En PowerShell
$env:PYTHONPATH="src"
python -c "from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram; notificar_alerta_telegram('Test', 'Bot funcionando!', 'alta')"
```

Si todo está bien, recibirás un mensaje en Telegram 🎉

## Uso en Jobs

```python
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram

# Alerta de alta prioridad (con sonido)
notificar_alerta_telegram(
    nombre="🚨 Error Crítico",
    descripcion="La cuenta X se desactivó",
    prioridad="alta",
    datos={
        "Cuenta": "ClienteX",
        "Error": "Pago rechazado"
    }
)

# Alerta informativa (sin sonido)
notificar_alerta_telegram(
    nombre="✅ Job Completado",
    descripcion="Sincronización exitosa",
    prioridad="baja",
    datos={"Total": 100, "Errores": 0}
)
```

## Niveles de Prioridad

| Prioridad | Emoji | Sonido | Uso |
|-----------|-------|--------|-----|
| **alta** | 🚨 | ✅ Sí | Errores críticos, cuentas desactivadas |
| **media** | ⚠️ | ❌ No | Advertencias, resúmenes con problemas |
| **baja** | ℹ️ | ❌ No | Información, completación de jobs |

## Notificaciones Configuradas

El sistema enviará automáticamente notificaciones para:

- 🚨 **Cuentas Meta Ads desactivadas** (alta)
- ⚠️ **Errores en sincronización** (media)
- ℹ️ **Resúmenes de jobs** (baja)
- 📊 **Métricas y reportes** (según configuración)

## Grupos de Telegram (Opcional)

Para compartir alertas con el equipo:

1. Crea un grupo en Telegram
2. Agrega el bot al grupo
3. Haz al bot administrador
4. Usa el script para obtener el `chat_id` del grupo
5. Usa ese `chat_id` específico en los jobs que quieras compartir

## Múltiples Chats

Puedes enviar a diferentes chats:

```python
# Chat principal (usa .env)
notificar_alerta_telegram(nombre="Alerta", descripcion="...")

# Chat específico
notificar_alerta_telegram(
    nombre="Alerta",
    descripcion="...",
    chat_id="-987654321"  # ID del grupo o usuario
)
```

## Troubleshooting

**No recibo mensajes:**
- ✅ Verifica que el token sea correcto
- ✅ Verifica que el chat_id sea correcto
- ✅ Asegúrate de haber enviado al menos 1 mensaje al bot
- ✅ Revisa los logs: `logger.error` mostrará el problema

**Error "Forbidden":**
- El bot no puede enviar mensajes porque no has iniciado conversación
- Solución: Envía `/start` al bot en Telegram

**Error "Chat not found":**
- El chat_id es incorrecto
- Solución: Usa el script helper para obtener el correcto

## Costo

**$0.00 USD** ✅

Telegram Bot API es completamente gratuito, sin límites de mensajes ni cargos ocultos.
