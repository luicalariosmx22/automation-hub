# 🚀 Dashboard de Jobs - Automation Hub

Dashboard web mejorado para monitorear y gestionar jobs automatizados.

## 🎯 Características

### 📊 Visualización
- **Vista en tiempo real**: Auto-refresh cada 30 segundos (pausable)
- **Estadísticas generales**: Total de jobs, activos, pendientes e inactivos
- **Horarios en México**: Todos los tiempos mostrados en UTC-7 (hora de México)
- **Estados visuales**: Badges de colores para identificar rápidamente el estado
- **Indicadores de urgencia**: Alertas para jobs atrasados o próximos a ejecutarse

### 🔍 Filtros y Búsqueda
- **Filtro por estado**: Ver solo activos, inactivos o todos
- **Búsqueda**: Buscar jobs por nombre o descripción
- **Ordenamiento**: Jobs ordenados alfabéticamente

### 📅 Información de Cada Job
- **Nombre y descripción**
- **Frecuencia de ejecución**: Diario, cada hora, cada X minutos, etc.
- **Última ejecución**: Fecha, hora y tiempo relativo ("hace 2h")
- **Próxima ejecución**: Fecha, hora y countdown ("En 15 min", "Atrasado 30 min")
- **Estado**: Habilitado/Deshabilitado

### ⚡ Acciones Rápidas
- **Ejecutar ahora**: Ejecuta el job manualmente de forma inmediata
- **Activar/Desactivar**: Toggle para habilitar o pausar jobs
- **Auto-refresh**: Pausar/reanudar actualización automática

## 🚀 Cómo Usar

### 1. Iniciar el Servidor

```bash
# Desde la raíz del proyecto
set PYTHONPATH=src
python dashboard/server.py
```

El servidor se iniciará en `http://localhost:5000`

### 2. Abrir el Dashboard

Abre tu navegador y ve a:
```
http://localhost:5000
```

### 3. Monitorear Jobs

El dashboard se actualizará automáticamente cada 30 segundos. Verás:

- **🟢 Verde**: Job activo y funcionando correctamente
- **🟡 Naranja**: Job pendiente de ejecución o nunca ejecutado
- **⚪ Gris**: Job deshabilitado
- **🔴 Rojo**: Job con problemas o atrasado

### 4. Ejecutar Jobs Manualmente

1. Encuentra el job que quieres ejecutar
2. Click en el botón **"▶️ Ejecutar ahora"**
3. Confirma la ejecución
4. El job se ejecutará inmediatamente y verás el resultado

### 5. Activar/Desactivar Jobs

1. Click en **"⏸️ Desactivar"** para pausar un job
2. Click en **"▶️ Activar"** para reanudar un job desactivado

## 🎨 Interfaz

### Panel Superior
- **Hora actual** (México, UTC-7)
- **Countdown de auto-refresh**
- **Estadísticas**: Total, Activos, Pendientes, Inactivos

### Controles
- **🔄 Actualizar**: Actualiza datos manualmente
- **⏸️ Pausar Auto-refresh**: Pausa la actualización automática
- **Filtro de estado**: Dropdown para filtrar por estado
- **Búsqueda**: Campo de texto para buscar jobs

### Cards de Jobs
Cada job se muestra en una tarjeta con:
- **Borde de color**: Indica estado visual
- **Badge de estado**: OK, Pendiente, Inactivo, etc.
- **Información detallada**: Frecuencia, última y próxima ejecución
- **Botones de acción**: Ejecutar ahora, Activar/Desactivar

## 📱 Responsive

El dashboard es completamente responsive y funciona en:
- 💻 Escritorio
- 📱 Tablet
- 📲 Móvil

## 🔧 Tecnologías

- **Backend**: Flask + Python
- **Frontend**: HTML5 + Tailwind CSS + Vanilla JavaScript
- **Database**: Supabase (PostgreSQL)
- **API**: REST con CORS habilitado

## 🐛 Troubleshooting

### El servidor no inicia

Verifica que:
1. Las variables de entorno estén configuradas en `.env`
2. `PYTHONPATH=src` esté configurado
3. El puerto 5000 esté disponible

### No se cargan los jobs

Verifica que:
1. El servidor Flask esté corriendo
2. La conexión a Supabase esté funcionando
3. La tabla `jobs_config` exista y tenga datos

### Error al ejecutar job manualmente

Verifica que:
1. El job esté registrado en `src/automation_hub/jobs/registry.py`
2. Todas las dependencias del job estén instaladas
3. Las credenciales necesarias estén en `.env`

## 📝 Endpoints API

El dashboard usa estos endpoints:

- `GET /api/jobs` - Lista todos los jobs
- `GET /api/jobs/pending` - Jobs pendientes de ejecución
- `GET /api/jobs/<name>` - Detalles de un job específico
- `POST /api/jobs/<name>/run` - Ejecuta un job manualmente
- `POST /api/jobs/<name>/toggle` - Activa/desactiva un job
- `POST /api/jobs/<name>/interval` - Actualiza intervalo de ejecución
- `GET /api/health` - Health check del servidor

## 🎯 Próximas Mejoras

- [ ] Historial de ejecuciones (últimas 10 ejecuciones)
- [ ] Logs en tiempo real
- [ ] Gráficas de métricas
- [ ] Notificaciones push
- [ ] Edición de intervalos desde UI
- [ ] Creación de jobs desde UI
- [ ] Exportar configuración

## 📄 Licencia

Parte del proyecto Automation Hub.
