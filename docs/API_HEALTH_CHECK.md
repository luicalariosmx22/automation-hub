# API Health Check Job

## 📋 Descripción

Job automático que verifica el estado de todos los tokens y APIs del sistema, detectando problemas antes de que afecten a los usuarios.

## 🎯 Servicios Verificados

1. **OpenAI API** - Generación de texto con GPT
2. **DeepSeek API** - Modelo de IA alternativo
3. **Gemini API** - Google AI para resúmenes
4. **Twilio (WhatsApp)** - Mensajería WhatsApp
5. **Google OAuth (GBP)** - Google Business Profile
6. **Meta/Facebook API** - Anuncios y publicaciones
7. **Telegram Bot** - Notificaciones
8. **Supabase** - Base de datos
9. **TikTok API** - Integración TikTok
10. **Google Calendar API** - Sincronización de calendarios

## ⚙️ Configuración

### Horario de Ejecución
- **8:00 AM** - Verificación matutina
- **8:00 PM** - Verificación nocturna

Programado con cron: `0 8,20 * * *`

### Notificaciones
- ✅ **Éxito**: Notificación silenciosa (opcional)
- ❌ **Fallo**: Alerta inmediata por Telegram con detalles

## 🚀 Uso

### Ejecutar Manualmente
```bash
python verificar_apis.py
```

### Ejecutar como Job
```python
from automation_hub.jobs.api_health_check import run

resultado = run()
print(resultado)
```

### Resultado
```python
{
    "job": "api.health_check",
    "timestamp": "2025-12-30T10:00:00",
    "total_servicios": 10,
    "servicios_ok": 9,
    "servicios_fallando": 1,
    "servicios_con_error": ["OpenAI API"],
    "resultados": {
        "OpenAI API": {
            "exitoso": False,
            "mensaje": "API Key inválida"
        },
        ...
    }
}
```

## 📧 Ejemplo de Notificación

### Alerta de Fallo
```
🚨 ALERTA: APIs/Tokens con Problemas

📊 Estado: 9/10 servicios funcionando
⏰ Hora: 2025-12-30 08:00:15

❌ Servicios fallando:

• OpenAI API
  └ API Key inválida

✅ Servicios funcionando:
• DeepSeek API
• Gemini API
• Twilio (WhatsApp)
• Google OAuth (GBP)
• Meta/Facebook API
• Telegram Bot
• Supabase
• TikTok API
• Google Calendar API
```

## 🔧 Instalación

### 1. Aplicar Migración SQL
```bash
# Conectarse a Supabase y ejecutar
psql -h your-db.supabase.co -U postgres -d postgres -f migrations/add_api_health_check_job.sql
```

O desde Supabase Dashboard:
1. Ir a SQL Editor
2. Ejecutar el contenido de `migrations/add_api_health_check_job.sql`

### 2. Verificar Registro
El job se registra automáticamente al importar el módulo `automation_hub.jobs.registry`.

### 3. Probar
```bash
python verificar_apis.py
```

## 🛠️ Troubleshooting

### Token "REDACTED"
Si un token contiene la palabra "REDACTED", el job lo marcará como inválido. Actualiza el `.env` con el token real.

### Timeout
El timeout por defecto es 10 segundos por API. Si hay problemas de red, algunos servicios pueden fallar temporalmente.

### Supabase Connection
Si falla la verificación de Supabase, verifica:
- `SUPABASE_URL` configurado
- `SUPABASE_KEY` válido
- Conexión de red

## 📝 Personalización

### Agregar Nuevo Servicio

1. Crear función de verificación en `api_health_check.py`:
```python
def verificar_mi_servicio() -> Tuple[bool, str]:
    """Verifica mi servicio."""
    try:
        # Tu lógica aquí
        return True, "OK"
    except Exception as e:
        return False, f"Error: {str(e)}"
```

2. Agregar al diccionario en `run()`:
```python
verificaciones = {
    ...
    "Mi Servicio": verificar_mi_servicio,
}
```

### Cambiar Horario

Editar en `jobs_config`:
```sql
UPDATE jobs_config 
SET schedule = '0 */6 * * *'  -- Cada 6 horas
WHERE nombre = 'api.health_check';
```

### Desactivar Notificaciones de Éxito

En `api_health_check.py`, comentar el bloque:
```python
# try:
#     from automation_hub.integrations.telegram.notifier import TelegramNotifier
#     telegram = TelegramNotifier()
#     ...
# except Exception as e:
#     ...
```

## 📊 Métricas

El job guarda su resultado en `jobs_executions` incluyendo:
- Timestamp de ejecución
- Total de servicios verificados
- Servicios OK vs fallando
- Detalles de cada error

## 🔐 Seguridad

- **Nunca** loguea tokens completos
- Solo reporta el estado (OK/Error)
- Usa timeouts para evitar bloqueos
- No almacena credenciales en BD

## 📚 Referencias

- [Documentación de Jobs](../docs/CREAR_JOBS.md)
- [Sistema de Notificaciones](../docs/GESTIONAR_NOTIFICACIONES.md)
- [Telegram Setup](../docs/TELEGRAM_SETUP.md)
