# 📋 Guía para Crear Nuevos Jobs

Esta guía establece el estándar para crear jobs en Automation Hub.

## 🎯 Estructura Estándar de un Job

Todos los jobs deben seguir esta estructura:

```python
"""
Job para [descripción breve].
"""
import logging
import os
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram
# ... otros imports necesarios

logger = logging.getLogger(__name__)

JOB_NAME = "categoria.nombre.frecuencia"  # ej: gbp.reviews.daily


def run(ctx=None):
    """
    Ejecuta el job de [descripción].
    
    1. [Paso 1]
    2. [Paso 2]
    3. [Paso 3]
    """
    logger.info(f"Iniciando job: {JOB_NAME}")
    
    # Obtener configuración desde env vars
    config_var = os.getenv("CONFIG_VAR", "default_value")
    
    # Crear cliente Supabase
    supabase = create_client_from_env()
    
    # Estadísticas del job
    stats = {
        "total": 0,
        "procesados": 0,
        "errores": 0
    }
    
    # === LÓGICA PRINCIPAL DEL JOB ===
    try:
        # Tu código aquí
        pass
        
    except Exception as e:
        logger.error(f"Error en job: {e}", exc_info=True)
        stats["errores"] += 1
    
    # === RESUMEN Y NOTIFICACIONES ===
    logger.info(f"Job {JOB_NAME} completado")
    logger.info(f"Procesados: {stats['procesados']}, Errores: {stats['errores']}")
    
    # Crear alerta y notificar por Telegram
    try:
        # Determinar prioridad
        if stats['errores'] > 0:
            prioridad = "alta"  # Errores críticos
        elif stats['procesados'] > 100:
            prioridad = "media"  # Muchos cambios
        else:
            prioridad = "baja"  # Normal
        
        descripcion = f"Job completado: {stats['procesados']} procesados"
        if stats['errores'] > 0:
            descripcion += f", ⚠️ {stats['errores']} errores"
        
        # Guardar en BD
        crear_alerta(
            supabase=supabase,
            nombre=f"Job {JOB_NAME} Completado",
            tipo="job_completado",
            nombre_nora="Sistema",
            descripcion=descripcion,
            evento_origen=JOB_NAME,
            datos={
                **stats,
                "job_name": JOB_NAME
            },
            prioridad=prioridad
        )
        
        # Notificar por Telegram
        notificar_alerta_telegram(
            nombre=f"📊 {JOB_NAME.upper()}",
            descripcion=descripcion,
            prioridad=prioridad,
            datos=stats
        )
    except Exception as e:
        logger.warning(f"No se pudo crear alerta: {e}")
```

## 📝 Reglas Obligatorias

### 1. **Siempre incluir alertas y notificaciones**

Todos los jobs DEBEN:
- ✅ Crear alerta en la tabla `alertas`
- ✅ Enviar notificación por Telegram
- ✅ Incluir estadísticas del proceso

### 2. **Importaciones requeridas**

```python
from automation_hub.db.repositories.alertas_repo import crear_alerta
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram
```

### 3. **Prioridades de alertas**

| Prioridad | Cuándo usarla | Emoji |
|-----------|---------------|-------|
| **alta** | Errores críticos, cuentas desactivadas, rechazos | 🚨 |
| **media** | Advertencias, cambios importantes, muchos registros | ⚠️ |
| **baja** | Completación normal, info | ℹ️ ✅ |

### 4. **Estadísticas mínimas**

Todos los jobs deben trackear:
```python
stats = {
    "total": 0,          # Total de items procesados
    "procesados": 0,     # Items exitosos
    "errores": 0,        # Items con error
    # ... campos específicos del job
}
```

### 5. **Manejo de errores**

```python
try:
    # Código del job
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    stats["errores"] += 1
    
    # Opcional: registrar en tabla de errores específica
    registrar_error(supabase, error_mensaje=str(e))
```

## 🎨 Emojis Recomendados

Para las notificaciones de Telegram:

| Tipo | Emoji | Ejemplo |
|------|-------|---------|
| Completado | ✅ | `✅ Reviews Sincronizadas` |
| Datos/Métricas | 📊 | `📊 Resumen: Sync Cuentas` |
| Error crítico | 🚨 | `🚨 Cuenta Desactivada` |
| Advertencia | ⚠️ | `⚠️ Anuncios Rechazados` |
| Información | ℹ️ | `ℹ️ Job Completado` |
| Dinero | 💰 | `💰 Budget Excedido` |
| Usuario | 👤 | `👤 Nueva Review` |
| Calendario | 📅 | `📅 Reporte Diario` |

## 📂 Ubicación de Archivos

```
src/automation_hub/jobs/
├── nombre_job_daily.py        # Tu nuevo job
├── registry.py                # Registrar aquí
└── __init__.py
```

## 🔧 Registro del Job

Después de crear tu job, regístralo en `registry.py`:

```python
from automation_hub.jobs import (
    gbp_reviews_daily,
    gbp_metrics_daily,
    tu_nuevo_job_daily,  # <-- Agregar aquí
)

register_job(gbp_reviews_daily.JOB_NAME, gbp_reviews_daily.run)
register_job(gbp_metrics_daily.JOB_NAME, gbp_metrics_daily.run)
register_job(tu_nuevo_job_daily.JOB_NAME, tu_nuevo_job_daily.run)  # <-- Y aquí
```

## 🗄️ Configuración en Base de Datos

Agregar a la tabla `jobs_config`:

```sql
INSERT INTO jobs_config (
    job_name,
    enabled,
    schedule_interval_minutes,
    next_run_at
) VALUES (
    'tu_categoria.nombre.daily',
    true,
    1440,  -- 24 horas
    NOW()
);
```

## 🧪 Testing Local

Antes de hacer commit:

```bash
# Cargar variables de entorno
Get-Content .env | ForEach-Object { 
    if ($_ -match '^([A-Z_]+)=(.+)$') { 
        Set-Item -Path "env:$($matches[1])" -Value $matches[2] 
    } 
}

# Ejecutar job
$env:PYTHONPATH="src"
python -m automation_hub.runners.run_job tu_categoria.nombre.daily

# Verificar en Telegram que recibiste la notificación
```

## ✅ Checklist Pre-Commit

Antes de hacer commit de un nuevo job, verifica:

- [ ] El job tiene `JOB_NAME` definido
- [ ] Importa `crear_alerta` y `notificar_alerta_telegram`
- [ ] Crea alerta en BD al finalizar
- [ ] Envía notificación por Telegram
- [ ] Tiene manejo de errores con try/except
- [ ] Registra estadísticas (`stats = {}`)
- [ ] Tiene logging apropiado
- [ ] Está registrado en `registry.py`
- [ ] Tiene docstring explicando qué hace
- [ ] Probado localmente y recibiste notificación en Telegram

## 📖 Ejemplos de Referencia

Ver estos jobs como ejemplos completos:
- [`meta_ads_cuentas_sync_daily.py`](../src/automation_hub/jobs/meta_ads_cuentas_sync_daily.py) - Detección de cambios + alertas por prioridad
- [`gbp_reviews_daily.py`](../src/automation_hub/jobs/gbp_reviews_daily.py) - Sincronización simple
- [`meta_ads_rechazos_daily.py`](../src/automation_hub/jobs/meta_ads_rechazos_daily.py) - Alertas agrupadas por cliente

## 🚀 Deployment

Una vez el job esté testeado localmente:

1. Commit y push a `main`
2. Railway desplegará automáticamente
3. Verificar logs en Railway
4. Verificar que llegó notificación de Telegram en producción
5. Monitorear primeras ejecuciones

## 💡 Tips

- **Siempre loggea**: Usa `logger.info()`, `logger.warning()`, `logger.error()`
- **Datos útiles**: Incluye en stats lo que te ayude a debugging
- **Prioridades correctas**: No todo es "alta", reserva para críticos
- **Mensajes claros**: Describe qué pasó, no solo números
- **Test primero**: Siempre ejecuta local antes de deploy
