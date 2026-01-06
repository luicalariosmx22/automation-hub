# 📹 Implementación YouTube Shorts - Resumen Ejecutivo

## ✅ Estado: COMPLETO

Integración completa de YouTube Shorts para subir videos automáticamente desde Facebook usando YouTube Data API v3.

---

## 📦 Componentes Implementados

### 1. Base de Datos (✅ Completo)

**Archivo:** `db/migrations/007_youtube_integration.sql`

**Tablas creadas:**

- **`youtube_conexiones`**: Almacena conexiones OAuth por cliente
  - `cliente_id` + `canal_id` (único por combinación)
  - `canal_titulo`, `refresh_token`, `access_token`, `token_expira_en`
  
- **`youtube_videos`**: Registro de videos subidos
  - Referencia a `conexion_id` y `cliente_id`
  - `video_id`, `video_url`, metadata del video
  - `source_type` + `source_id` para rastrear origen

### 2. Repository (✅ Completo)

**Archivo:** `src/automation_hub/db/repositories/youtube_conexiones_repo.py`

**Clase:** `YouTubeConexionesRepository`

**Métodos:**
- `save_conexion()` - Guarda/actualiza conexión con upsert
- `get_conexion()` - Obtiene conexión por cliente + canal (opcional)
- `get_conexiones_cliente()` - Lista todas las conexiones de un cliente
- `update_access_token()` - Refresca access token cuando expira
- `delete_conexion()` - Elimina conexión
- `is_connected()` - Verifica si cliente tiene YouTube conectado

### 3. OAuth Manager (✅ Completo)

**Archivo:** `src/automation_hub/integrations/youtube/oauth.py`

**Clase:** `YouTubeOAuthManager`

**Scopes:** `https://www.googleapis.com/auth/youtube.upload`

**Métodos:**
- `get_authorization_url()` - Genera URL OAuth con `access_type=offline` + `prompt=consent`
- `exchange_code_for_tokens()` - Intercambia código por tokens
- `get_canal_info()` - **NUEVO:** Llama `channels.list(mine=true)` para obtener `canal_id` y `canal_titulo`
- `refresh_access_token()` - Refresca tokens expirados
- `validate_and_refresh_if_needed()` - Validación automática + refresh
- `get_youtube_service()` - Crea servicio autenticado

### 4. Upload Service (✅ Completo)

**Archivo:** `src/automation_hub/integrations/youtube/upload.py`

**Clase:** `YouTubeUploadService`

**Métodos:**
- `validate_video_for_shorts()` - Valida duración <=180s y aspect ratio (9:16 o 1:1) usando `ffprobe`
- `upload_video()` - Sube video con `MediaFileUpload` resumable (chunks de 10MB)
- `get_video_processing_status()` - Consulta estado de procesamiento

**Nota:** "Shorts" no es endpoint separado, usa `videos.insert` estándar. YouTube detecta automáticamente por duración y orientación.

### 5. Servicio Principal (✅ Completo)

**Archivo:** `src/automation_hub/integrations/youtube/youtube_service.py`

**Clase:** `YouTubeService`

**Flujo OAuth completo:**
1. `get_authorization_url()` - Genera URL
2. `handle_oauth_callback()` - Procesa callback:
   - Intercambia código por tokens
   - **Llama `channels.list(mine=true)`** para obtener canal
   - Guarda `canal_id` + `canal_titulo` + tokens en BD

**Gestión de canales:**
- `get_canales_conectados()` - Lista canales por cliente
- `disconnect_youtube()` - Desconecta canal
- `is_connected()` - Verifica conexión

**Upload automático:**
- `get_youtube_service_for_cliente()` - Servicio autenticado con refresh automático
- `upload_video()` - Sube video y registra en BD
- `get_video_status()` - Consulta estado

### 6. Rutas Web (✅ Completo)

**Archivo:** `src/automation_hub/integrations/youtube/routes.py`

**Blueprint:** `youtube_bp` en `/integraciones/youtube`

**Endpoints:**

#### `GET /integraciones/youtube/connect`
- Query param: `cliente_id`
- Muestra **warning HTML** sobre permisos de OWNER
- Genera URL de autorización
- Redirige a Google OAuth

#### `GET /integraciones/youtube/callback`
- Query params: `code`, `state` (cliente_id)
- Procesa callback OAuth
- Llama `channels.list(mine=true)` para obtener canal
- Guarda conexión en BD
- Muestra página de éxito con `canal_titulo` + `canal_id`

#### `POST /integraciones/youtube/disconnect/<conexion_id>`
- Elimina conexión

#### `GET /integraciones/youtube/canales/<cliente_id>`
- Lista canales conectados en JSON

### 7. Job Automático (✅ Completo)

**Archivo:** `src/automation_hub/jobs/youtube_shorts_daily.py`

**Configuración:**
- Límite: 5 videos por ejecución
- Delay: 120 segundos entre videos
- Frecuencia: 1440 minutos (24 horas)

**Flujo:**
1. Busca publicaciones de Facebook con video (`publicada_gbp = true`)
2. Filtra últimos 7 días
3. Verifica que cliente tenga YouTube conectado
4. Descarga video de Supabase Storage a temporal
5. Sube a YouTube con `privacy_status = public`
6. Valida Shorts (duración y aspect ratio)
7. Registra en `youtube_videos` con `source_type = 'facebook_post'`
8. Envía notificación Telegram con URL del video
9. Limpia archivo temporal

**Archivo:** `migrations/add_youtube_shorts_job.sql`
- Crea configuración en `jobs_config`
- `intervalo_minutos = 1440` (diario)
- `timeout_seconds = 1800` (30 min)

### 8. Documentación (✅ Completo)

**Archivo:** `docs/YOUTUBE_SHORTS_SETUP.md`

**Incluye:**
- Configuración en Google Cloud Console
- Creación de OAuth credentials
- Configuración de OAuth Consent Screen
- Instrucciones de conexión de canal
- Ejemplos de uso
- Estructura de datos
- Endpoints API
- Troubleshooting
- Referencias

**Archivo:** `youtube_client_secrets.json.template`
- Template para credenciales OAuth

**Archivo:** `probar_youtube.py`
- Script interactivo para probar conexión
- Genera URLs de autorización
- Lista canales conectados

---

## 🎯 Requisitos Cumplidos

### ✅ OAuth "Conectar canal"
- Endpoint `/integraciones/youtube/connect` con warning sobre OWNER
- Scopes: `https://www.googleapis.com/auth/youtube.upload`
- `access_type=offline` + `prompt=consent` para obtener refresh_token
- Callback guarda tokens + llama `channels.list(mine=true)` para obtener `canal_id` y `canal_titulo`

### ✅ Modelo/DB
- Tabla `youtube_conexiones` con `canal_id`, `canal_titulo`, `refresh_token`
- Tabla `youtube_videos` con referencia a `conexion_id`
- Índices para búsquedas eficientes

### ✅ Subida de videos
- Función `upload_youtube_video()` con `MediaFileUpload` resumable
- Usa `videos.insert` (no hay endpoint separado para Shorts)
- Guarda `videoId` + URL en BD
- Tracking con `source_type` + `source_id`

### ✅ UI/Warning
- HTML con advertencia clara: **solo OWNER puede conectar**
- Explica que Manager/Editor no funcionan con APIs
- Página de éxito muestra `canal_titulo` + `canal_id`
- Endpoint para listar canales conectados

---

## 📋 Checklist de Implementación

### Base de Datos
- [x] Migración `007_youtube_integration.sql`
- [x] Tabla `youtube_conexiones` con unique constraint
- [x] Tabla `youtube_videos` con foreign keys
- [x] Índices optimizados

### Backend
- [x] `YouTubeConexionesRepository` con CRUD completo
- [x] `YouTubeOAuthManager` con `get_canal_info()`
- [x] `YouTubeUploadService` con validación Shorts
- [x] `YouTubeService` con flujo OAuth completo
- [x] Refresh automático de tokens

### Web/API
- [x] Blueprint `youtube_bp` registrado
- [x] Endpoint `/connect` con warning HTML
- [x] Endpoint `/callback` con `channels.list`
- [x] Endpoint `/disconnect`
- [x] Endpoint `/canales` para listar

### Jobs
- [x] `youtube_shorts_daily.py` con límites y delays
- [x] Descarga de videos de Supabase
- [x] Validación de Shorts con ffprobe
- [x] Notificaciones Telegram
- [x] Limpieza de archivos temporales
- [x] Configuración en `jobs_config`

### Documentación
- [x] Guía completa en `YOUTUBE_SHORTS_SETUP.md`
- [x] Template de credenciales
- [x] Script de prueba `probar_youtube.py`
- [x] Comentarios en código
- [x] Docstrings completos

---

## 🚀 Próximos Pasos

### 1. Aplicar Migración

```sql
-- En Supabase SQL Editor
-- Ejecutar: db/migrations/007_youtube_integration.sql
```

### 2. Configurar Credenciales

1. Crear proyecto en Google Cloud Console
2. Habilitar YouTube Data API v3
3. Crear OAuth client ID (Web application)
4. Descargar credenciales como `youtube_client_secrets.json`
5. Configurar redirect URIs

### 3. Variables de Entorno

```bash
# .env
YOUTUBE_CLIENT_SECRETS_FILE=youtube_client_secrets.json
```

### 4. Registrar Blueprint

En tu aplicación Flask principal:

```python
from automation_hub.integrations.youtube.routes import youtube_bp

app.register_blueprint(youtube_bp)
```

### 5. Activar Job

```sql
-- En Supabase SQL Editor
-- Ejecutar: migrations/add_youtube_shorts_job.sql
```

### 6. Probar Conexión

```bash
python probar_youtube.py
```

---

## ⚠️ Advertencias Importantes

### 1. Permisos de OWNER
- **Solo el propietario del canal** puede conectar por API
- Manager/Editor en YouTube Studio **NO funcionan**
- Verificar en YouTube Studio > Settings > Permissions

### 2. OAuth Consent Screen
- Debe estar configurado en Google Cloud Console
- Agregar scope `youtube.upload`
- En modo "Testing", agregar emails de test users

### 3. Shorts Detection
- No hay endpoint separado para Shorts
- YouTube detecta automáticamente por:
  - Duración ≤ 60s (tolerancia hasta 180s)
  - Aspect ratio vertical (9:16) o cuadrado (1:1)

### 4. Rate Limits
- Job limita a 5 videos por ejecución
- 120 segundos de delay entre videos
- YouTube tiene límites de API (10,000 units/día por proyecto)

---

## 📊 Métricas

**Archivos creados/modificados:** 12

- `db/migrations/007_youtube_integration.sql`
- `src/automation_hub/db/repositories/youtube_conexiones_repo.py`
- `src/automation_hub/integrations/youtube/oauth.py` (modificado)
- `src/automation_hub/integrations/youtube/upload.py`
- `src/automation_hub/integrations/youtube/youtube_service.py`
- `src/automation_hub/integrations/youtube/routes.py`
- `src/automation_hub/integrations/youtube/__init__.py` (modificado)
- `src/automation_hub/jobs/youtube_shorts_daily.py`
- `migrations/add_youtube_shorts_job.sql`
- `youtube_client_secrets.json.template`
- `docs/YOUTUBE_SHORTS_SETUP.md`
- `probar_youtube.py`

**Líneas de código:** ~2,500

**Tablas de BD:** 2

**Endpoints web:** 4

**Jobs:** 1

---

## 🎉 Conclusión

Implementación completa de YouTube Shorts lista para usar. Sigue los "Próximos Pasos" para configurar credenciales y empezar a subir videos automáticamente desde Facebook.

**Documentación completa en:** `docs/YOUTUBE_SHORTS_SETUP.md`
