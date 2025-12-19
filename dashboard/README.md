# 🎛️ Dashboard de Gestión de Jobs

Dashboard web local para gestionar los jobs de automation-hub.

## 🚀 Uso Rápido

1. **Inicia el servidor:**
```bash
PYTHONPATH=src python dashboard/server.py
```

2. **Abre tu navegador:**
```
http://localhost:5000
```

3. **Listo!** El dashboard usa automáticamente las credenciales de tu `.env`

## ✨ Funcionalidades

### Ver Jobs
- Lista de todos los jobs configurados
- Estado (Activo/Inactivo)  
- Última y próxima ejecución
- Intervalo de ejecución
- Errores recientes (si los hay)

### Gestionar Jobs

**Pausar/Activar:**
- Botón "Pausar" para deshabilitar un job
- Botón "Activar" para habilitar un job pausado

**Ejecutar Inmediatamente:**
- Botón "▶ Ejecutar" programa el job para la próxima corrida del cron
- Establece `next_run_at = NOW()`

**Cambiar Intervalo:**
- Botón "⚙️ Intervalo" para modificar frecuencia
- Opciones: 10min, 30min, 1h, 3h, 6h, 12h, 24h
- O ingresa minutos personalizados

## 🔧 Arquitectura

- **Backend:** Flask server (`server.py`)
  - Lee credenciales desde `.env`
  - Expone API REST en `http://localhost:5000/api`
  - Usa repositorios existentes de automation-hub

- **Frontend:** HTML + Tailwind CSS (`jobs-manager-local.html`)
  - Se conecta al backend local (NO a Supabase directo)
  - Actualización en tiempo real
  - Diseño responsive

## 📡 Endpoints API

- `GET /api/jobs` - Lista todos los jobs
- `GET /api/jobs/pending` - Jobs listos para ejecutar
- `GET /api/jobs/<name>` - Detalle de un job
- `POST /api/jobs/<name>/toggle` - Habilitar/deshabilitar
- `POST /api/jobs/<name>/interval` - Cambiar intervalo
- `POST /api/jobs/<name>/run-now` - Ejecutar ahora
- `POST /api/jobs` - Crear nuevo job
- `GET /api/health` - Health check

## 🔒 Seguridad

✅ **Sin credenciales expuestas:** Todo se lee del `.env` local
✅ **Solo localhost:** El servidor corre en tu máquina
✅ **Sin git:** Las credenciales nunca se suben al repo

## 📝 Requisitos

```bash
pip install flask flask-cors
```

(Ya incluido en `requirements.txt`)
