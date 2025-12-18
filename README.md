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
│       ├── jobs/
│       │   ├── __init__.py
│       │   └── registry.py    # Registro de jobs
│       └── runners/
│           ├── __init__.py
│           └── run_job.py     # CLI para ejecutar jobs
├── .env.example
├── .gitignore
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
pip install -e .
```

4. **Configurar variables de entorno:**

```bash
cp .env.example .env
# Editar .env según necesidad
```

## Uso

### Ejecutar un Job

```bash
python -m automation_hub.runners.run_job <job_name>
```

### Listar Jobs Disponibles

Si no hay jobs registrados o se proporciona un nombre inválido, el runner mostrará la lista de jobs disponibles:

```bash
python -m automation_hub.runners.run_job
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

- `LOG_LEVEL`: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `ENVIRONMENT`: Entorno de ejecución (development, production, etc.)
- `TZ`: Zona horaria (default: UTC)

## Desarrollo

El proyecto está estructurado para soportar múltiples jobs de forma escalable. Cada job es simplemente una función callable registrada en el sistema.

## Licencia

MIT
