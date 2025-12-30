# 🔔 Gestor de Notificaciones Telegram

Sistema completo para gestionar contactos y configuración de notificaciones por Telegram.

## 🎯 Características

### 👥 Gestión de Contactos
- **Agregar contactos**: Usuarios individuales o grupos de Telegram
- **Editar configuración**: Modificar permisos y filtros en cualquier momento
- **Activar/Desactivar**: Control on/off sin eliminar la configuración
- **Eliminar contactos**: Borrado permanente de contactos

### 🎯 Filtros Avanzados
- **Por Jobs**: Selecciona qué jobs pueden enviar notificaciones a cada contacto
- **Por Prioridad**: Filtra por Alta, Media o Baja prioridad
- **Por Tipo de Alerta**: Configura tipos específicos de alertas
- **Cliente/Sistema**: Organiza contactos por cliente o nivel sistema

### 📊 Estadísticas en Tiempo Real
- Total de contactos configurados
- Contactos activos vs inactivos
- Cantidad de clientes únicos
- Contactos a nivel sistema

### 🔍 Búsqueda y Filtros
- **Buscar por nombre** o Chat ID
- **Filtrar por cliente**
- **Filtrar por estado** (activo/inactivo)
- Combinación de múltiples filtros

## 🚀 Acceso

### Opción 1: Desde el Dashboard Principal
1. Abre el dashboard: http://localhost:5000
2. Click en el botón **"💬 Notificaciones"** en el header

### Opción 2: Directo
Abre tu navegador en: http://localhost:5000/notifications-manager.html

## 📝 Cómo Usar

### ➕ Agregar un Nuevo Contacto

1. Click en **"➕ Agregar Contacto"**
2. Completa el formulario:
   - **Cliente / Nombre Nora**: Nombre del cliente o "Sistema"
   - **Chat ID**: El ID del chat de Telegram (número)
   - **Nombre del Contacto**: Nombre descriptivo
   - **Jobs Permitidos**: Selecciona jobs específicos (vacío = todos)
   - **Prioridades**: Alta, Media, Baja (vacío = todas)
   - **Tipos de Alerta**: Separados por comas (vacío = todos)
   - **Notas**: Información adicional
   - **Estado**: Marcar si está activo

3. Click en **"💾 Guardar"**

### ✏️ Editar un Contacto

1. Encuentra el contacto en la lista
2. Click en **"✏️ Editar"**
3. Modifica los campos necesarios
4. Click en **"💾 Guardar"**

### 🔄 Activar/Desactivar

- Click en **"⏸️ Desactivar"** para pausar notificaciones sin borrar configuración
- Click en **"▶️ Activar"** para reanudar notificaciones

### 🗑️ Eliminar Contacto

1. Click en **"🗑️ Eliminar"**
2. Confirma la acción (es permanente)

## 💡 Ejemplos de Configuración

### Admin - Recibe TODO
```
Cliente: Sistema
Chat ID: 5674082622
Nombre: Charlie - Admin
Jobs: (vacío - todos los jobs)
Prioridades: (vacío - todas)
Activo: ✅
```

### Cliente - Solo Alertas Críticas
```
Cliente: Luis
Chat ID: 1234567890
Nombre: Luis - Cliente
Jobs: (vacío - todos)
Prioridades: ✅ Alta
Activo: ✅
```

### Equipo - Jobs Específicos
```
Cliente: Sistema
Chat ID: -987654321
Nombre: Equipo Meta Ads
Jobs: ✅ meta_ads.rechazos.daily
     ✅ meta_ads.cuentas.sync.daily
Prioridades: ✅ Alta  ✅ Media
Activo: ✅
```

## 🎨 Interfaz

### Panel Superior
- Total de contactos
- Contactos activos
- Clientes únicos
- Contactos de sistema

### Controles
- **Agregar Contacto**: Crear nuevo contacto
- **Actualizar**: Refrescar datos
- **Filtro Cliente**: Filtrar por cliente específico
- **Filtro Estado**: Activos/Inactivos
- **Búsqueda**: Buscar por nombre o Chat ID

### Cards de Contactos
Cada contacto muestra:
- **Estado**: Badge activo/inactivo
- **Cliente y Chat ID**
- **Jobs permitidos**: Lista o "TODOS"
- **Prioridades**: Badges de color
- **Notas**: Información adicional
- **Botones**: Editar, Activar/Desactivar, Eliminar

## 🔍 Cómo Obtener el Chat ID

### Para Usuario Individual:
1. Habla con [@userinfobot](https://t.me/userinfobot) en Telegram
2. Envía `/start`
3. El bot te mostrará tu Chat ID

### Para Grupo:
1. Agrega [@userinfobot](https://t.me/userinfobot) al grupo
2. Envía `/start` en el grupo
3. El bot mostrará el Chat ID del grupo (negativo)
4. Quita el bot del grupo

## 📋 Estructura de Datos

### Jobs Disponibles
Los jobs actualmente disponibles para configurar son:
- `gbp.reviews.daily`
- `gbp.metrics.daily`
- `meta_ads.rechazos.daily`
- `meta_ads.cuentas.sync.daily`
- `meta_ads.anuncios.daily`
- `calendar.sync`
- `calendar.daily.summary`
- `meta_ads.daily.sync`
- `meta_ads.weekly.report`
- `meta.to_gbp.daily`

### Prioridades
- **Alta** 🔴: Alertas críticas que requieren atención inmediata
- **Media** 🟡: Notificaciones importantes pero no urgentes
- **Baja** 🔵: Información general y reportes

### Tipos de Alerta (Ejemplos)
- `cuenta_desactivada`: Cuenta de Meta Ads desactivada
- `meta_ads_rechazados`: Anuncios rechazados
- `review_negativa`: Review de 1-2 estrellas en GBP
- `error_api`: Error en llamada a API externa
- `job_failed`: Job falló al ejecutarse

## 🔧 API Endpoints

El gestor usa estos endpoints:

- `GET /api/notifications/contacts` - Lista todos los contactos
- `POST /api/notifications/contacts` - Crea un contacto
- `GET /api/notifications/contacts/<id>` - Obtiene un contacto
- `PUT /api/notifications/contacts/<id>` - Actualiza un contacto
- `POST /api/notifications/contacts/<id>/toggle` - Activa/desactiva
- `DELETE /api/notifications/contacts/<id>` - Elimina un contacto

## 🎯 Mejores Prácticas

1. **Usa "Sistema"** para contactos administrativos que reciben todo
2. **Filtra por prioridad** para evitar spam a clientes
3. **Agrupa notificaciones** usando grupos de Telegram para equipos
4. **Documenta en Notas** el propósito de cada configuración
5. **Desactiva en lugar de eliminar** para mantener historial
6. **Configura jobs específicos** para equipos especializados

## 🐛 Troubleshooting

### No llegan notificaciones
✅ Verifica que el contacto esté **activo**
✅ Confirma que el **Chat ID** sea correcto
✅ Revisa los **filtros** (jobs, prioridades, tipos)
✅ Asegúrate que el bot de Telegram esté en el chat/grupo

### Chat ID incorrecto
- IDs de usuarios son números positivos
- IDs de grupos son números negativos
- No incluyas letras ni símbolos

### No aparecen jobs en el selector
- Verifica que el servidor Flask esté corriendo
- Revisa que los jobs estén registrados en `registry.py`
- Refresca la página

## 📄 Base de Datos

Los contactos se guardan en la tabla `notificaciones_telegram_config` con estos campos:

```sql
- id: ID único del contacto
- nombre_nora: Cliente o "Sistema"
- chat_id: ID del chat de Telegram
- nombre_contacto: Nombre descriptivo
- jobs_permitidos: Array de nombres de jobs (NULL = todos)
- prioridades_permitidas: Array ['alta','media','baja'] (NULL = todas)
- tipos_alerta_permitidos: Array de tipos (NULL = todos)
- activo: Boolean
- notas: Texto libre
- created_at: Fecha de creación
- updated_at: Última actualización
```

---

**Powered by Nora AI** 🤖
