# 🚀 Job de Verificación de APIs/Tokens Creado

## ✅ Lo que se creó

### 1. **Job Principal** 
📄 [src/automation_hub/jobs/api_health_check.py](src/automation_hub/jobs/api_health_check.py)

Job que verifica 10 servicios críticos:
- OpenAI API
- DeepSeek API  
- Gemini API
- Twilio (WhatsApp)
- Google OAuth (GBP)
- Meta/Facebook API
- Telegram Bot
- Supabase
- TikTok API
- Google Calendar API

### 2. **Script de Ejecución Manual**
📄 [verificar_apis.py](verificar_apis.py)

Ejecutar con: `python verificar_apis.py`

### 3. **Migración SQL**
📄 [migrations/add_api_health_check_job.sql](migrations/add_api_health_check_job.sql)

Configura el job en `jobs_config` para ejecutarse:
- **8:00 AM** - Verificación matutina
- **8:00 PM** - Verificación nocturna

### 4. **Documentación**
📄 [docs/API_HEALTH_CHECK.md](docs/API_HEALTH_CHECK.md)

Guía completa de uso y personalización.

### 5. **Registro del Job**
✅ Actualizado [src/automation_hub/jobs/registry.py](src/automation_hub/jobs/registry.py) para incluir el nuevo job.

## 🎯 Cómo Funciona

1. El job verifica cada API/token haciendo una llamada real a cada servicio
2. Si detecta fallos, envía una **alerta inmediata por Telegram** con:
   - Lista de servicios fallando
   - Detalle del error de cada uno
   - Lista de servicios funcionando
3. Si todo está OK, envía notificación silenciosa (opcional)

## 📱 Ejemplo de Notificación

```
🚨 ALERTA: APIs/Tokens con Problemas

📊 Estado: 7/10 servicios funcionando
⏰ Hora: 2025-12-30 13:43:55

❌ Servicios fallando:

• Twilio (WhatsApp)
  └ Credenciales inválidas

• Google OAuth (GBP)
  └ Refresh token inválido o expirado

• Google Calendar API
  └ Refresh token inválido o expirado

✅ Servicios funcionando:
• OpenAI API
• DeepSeek API
• Gemini API
• Meta/Facebook API
• Telegram Bot
• Supabase
• TikTok API
```

## 🚀 Próximos Pasos

### 1. Aplicar Migración
```bash
# Conectarse a Supabase y ejecutar:
psql -h <tu-db>.supabase.co -U postgres -d postgres -f migrations/add_api_health_check_job.sql
```

O desde Supabase Dashboard → SQL Editor → ejecutar el contenido del archivo.

### 2. Verificar que Funciona
```bash
python verificar_apis.py
```

### 3. Activar el Job
El job ya está configurado para ejecutarse automáticamente 2 veces al día (8 AM y 8 PM).

### 4. Arreglar Tokens Fallando (Opcional)
Los servicios que fallaron en la prueba:
- **Twilio**: Token es "REDACTED", necesita el valor real
- **Google OAuth (GBP)**: Refresh token expirado, regenerar
- **Google Calendar**: Refresh token expirado, regenerar

## 🔧 Personalización

### Cambiar Horario
Editar `schedule` en la migración SQL o actualizar directamente en `jobs_config`:
```sql
UPDATE jobs_config 
SET schedule = '0 */4 * * *'  -- Cada 4 horas
WHERE nombre = 'api.health_check';
```

### Agregar Nuevo Servicio
En [api_health_check.py](src/automation_hub/jobs/api_health_check.py):

```python
def verificar_mi_api() -> Tuple[bool, str]:
    try:
        # Tu verificación aquí
        return True, "OK"
    except Exception as e:
        return False, f"Error: {str(e)}"

# Agregar al diccionario en run()
verificaciones = {
    ...
    "Mi API": verificar_mi_api,
}
```

### Desactivar Notificación de Éxito
Comentar el bloque de notificación de éxito en la línea ~445 del job.

## 📊 Resultado de la Prueba

```
Total servicios: 10
✅ Funcionando: 7
❌ Con problemas: 3

Servicios OK:
- OpenAI API
- DeepSeek API
- Gemini API
- Meta/Facebook API
- Telegram Bot
- Supabase
- TikTok API

Servicios con problemas:
- Twilio (WhatsApp): Credenciales inválidas
- Google OAuth (GBP): Refresh token expirado
- Google Calendar API: Refresh token expirado
```

✅ **El job está funcionando correctamente y ya te envió una notificación a Telegram!**

## 📚 Recursos

- [Documentación Completa](docs/API_HEALTH_CHECK.md)
- [Crear Jobs](docs/CREAR_JOBS.md)
- [Notificaciones Telegram](docs/GESTIONAR_NOTIFICACIONES.md)
