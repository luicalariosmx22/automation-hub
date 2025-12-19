# Automation Hub

Sistema de gestión de múltiples cron jobs en Python.

## Estructura del Proyecto

```
automation-hub/
├── src/
│   └── automation_hub/
│       ├── __init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py    # Configuración desde env vars
│       │   └── logging.py     # Setup de logging
│       ├── db/
│       │   ├── __init__.py
│       │   ├── supabase_client.py
│       │   └── repositories/
│       │       ├── __init__.py
│       │       ├── gbp_locations_repo.py
│       │       ├── gbp_reviews_repo.py
│       │       └── gbp_metrics_repo.py
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── google/
│       │   │   ├── __init__.py
│       │   │   └── oauth.py
│       │   └── gbp/
│       │       ├── __init__.py
│       │       ├── reviews_v4.py
│       │       └── performance_v1.py
│       ├── jobs/
│       │   ├── __init__.py
│       │   ├── registry.py    # Registro de jobs
│       │   ├── gbp_reviews_daily.py
│       │   └── gbp_metrics_daily.py
│       └── runners/
│           ├── __init__.py
│           └── run_job.py     # CLI para ejecutar jobs
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Instalación

1. **Crear entorno virtual:**

```bash
python -m venv venv
```

2. **Activar entorno virtual:**

- Windows:
  ```bash
  venv\Scripts\activate
  ```

- Linux/Mac:
  ```bash
  source venv/bin/activate
  ```

3. **Instalar dependencias:**

```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno:**

```bash
cp .env.example .env
# Editar .env según necesidad
```

## Uso

### Jobs Disponibles

El sistema incluye los siguientes jobs:

- **`gbp.reviews.daily`**: Sincroniza reviews de Google Business Profile
- **`gbp.metrics.daily`**: Sincroniza métricas diarias de GBP

### Ejecutar un Job

```bash
PYTHONPATH=src python -m automation_hub.runners.run_job <job_name>
```

Ejemplos:

```bash
# Sincronizar reviews
PYTHONPATH=src python -m automation_hub.runners.run_job gbp.reviews.daily

# Sincronizar métricas
PYTHONPATH=src python -m automation_hub.runners.run_job gbp.metrics.daily
```

### Ejecutar Múltiples Jobs en Batch

Para ejecutar varios jobs en secuencia (ideal para Railway Cron):

```bash
PYTHONPATH=src JOB_LIST=gbp.reviews.daily,gbp.metrics.daily python -m automation_hub.runners.run_batch
```

O usando grupos predefinidos:

```bash
PYTHONPATH=src JOB_GROUP=daily python -m automation_hub.runners.run_batch
```

Grupos disponibles:
- `tenmin`: Jobs cada 10 minutos
- `hourly`: Jobs cada hora
- `daily`: Jobs diarios (incluye GBP reviews y metrics)

Variables opcionales:
- `FAIL_FAST=true`: Detiene al primer error (default: false)

### Listar Jobs Disponibles

Si no hay jobs registrados o se proporciona un nombre inválido, el runner mostrará la lista de jobs disponibles:

```bash
PYTHONPATH=src python -m automation_hub.runners.run_job
```

### Exit Codes

- `0`: Job ejecutado exitosamente
- `1`: Error durante la ejecución del job
- `2`: Job no encontrado o argumentos inválidos

## Registrar un Nuevo Job

Para agregar un nuevo job, créalo en un módulo dentro de `src/automation_hub/jobs/` y regístralo:

```python
from automation_hub.jobs.registry import register_job

def mi_job():
    print("Ejecutando mi job")
    # Lógica del job aquí

# Registrar el job
register_job("mi_job", mi_job)
```

## Variables de Entorno

Consulta `.env.example` para ver todas las variables disponibles:

### Configuración General
- `LOG_LEVEL`: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `ENVIRONMENT`: Entorno de ejecución (development, production, etc.)
- `TZ`: Zona horaria (default: UTC)

### Supabase (requerido para jobs GBP)
- `SUPABASE_URL`: URL del proyecto Supabase
- `SUPABASE_KEY`: API key de Supabase

### Google OAuth (requerido para jobs GBP)
- `GOOGLE_CLIENT_ID`: Client ID de Google Cloud
- `GOOGLE_CLIENT_SECRET`: Client Secret de Google Cloud
- `GBP_REFRESH_TOKEN`: Refresh token de OAuth

### GBP Jobs (opcional)
- `GBP_NOMBRE_NORA`: Filtro por tenant (opcional)
- `GBP_METRICS`: Métricas a obtener (default: `WEBSITE_CLICKS,CALL_CLICKS`)
- `GBP_DAYS_BACK`: Días hacia atrás para métricas (default: 30)

### Batch Runner (opcional)
- `JOB_LIST`: Lista de jobs separados por coma (ej: `job1,job2`)
- `JOB_GROUP`: Grupo predefinido (`tenmin`, `hourly`, `daily`)
- `FAIL_FAST`: Detener al primer error (`true`/`false`, default: `false`)

## Desarrollo

El proyecto está estructurado para soportar múltiples jobs de forma escalable.

### Estructura de un Job

Cada job debe:
1. Definir `JOB_NAME` como constante
2. Implementar función `run(ctx=None)`
3. Manejar logging apropiadamente
4. Registrarse en `registry.py`

### Jobs GBP Implementados

**`gbp.reviews.daily`**: Sincroniza reviews de Google Business Profile
- Lee locaciones activas desde Supabase
- Descarga reviews usando GBP API v4
- Inserta/actualiza en tabla `gbp_reviews`

**`gbp.metrics.daily`**: Sincroniza métricas diarias de GBP
- Lee locaciones activas desde Supabase
- Descarga métricas usando Performance API v1
- Inserta/actualiza en tabla `gbp_metrics_daily`

## Licencia

MIT
