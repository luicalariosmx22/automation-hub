# Job: Meta Media Download Daily

## 📋 Descripción

Job automatizado que descarga imágenes y videos de publicaciones de Facebook/Instagram recibidas vía webhooks y las almacena en Supabase Storage.

**✨ Características:**
- 🔄 Reintentos automáticos (máx. 5 intentos)
- 📊 Tracking completo de estado (`media_status`, `media_attempts`, `media_last_error`)
- 🛡️ Idempotencia (no reprocesa archivos existentes)
- ⚡ Procesamiento por lotes (50 publicaciones/15 min)
- 🎯 Filtrado inteligente (excluye stories/historias)

## 🎯 Propósito

Cuando llegan webhooks de Meta con nuevas publicaciones, estas contienen URLs externas (Facebook/Instagram) de las imágenes y videos. Este job:

1. **Descarga** el contenido multimedia desde las URLs de Facebook
2. **Almacena** los archivos en Supabase Storage
3. **Actualiza** la base de datos con las URLs públicas de Supabase
4. **Garantiza** disponibilidad permanente del contenido (independiente de Facebook)

## 🔧 Configuración

- **Nombre del job:** `meta_media_download_daily`
- **Intervalo:** Cada 15 minutos
- **Batch size:** 50 publicaciones por ejecución
- **Timeout:** 10 minutos
- **Reintentos:** 3 intentos máximo
- **Prioridad:** 50 (media-alta)

## 📊 Proceso

### 1. Identificar Publicaciones Pendientes

Busca en `meta_publicaciones_webhook` publicaciones que cumplan:

- ✅ `imagen_url IS NOT NULL` (hay URL para descargar)
- ✅ `imagen_local IS NULL` o `video_local IS NULL` (no descargado)
- ✅ `tipo_item IN ('photo', 'video')`
- ✅ `mensaje IS NOT NULL` (excluye stories/historias)
- ✅ `media_status != 'success'` (no exitosas)
- ✅ `media_attempts < 5` (no excedió reintentos)

### 2. Descargar Contenido

Para cada publicación pendiente:

```python
# Descarga desde URL de Facebook
response = requests.get(imagen_url, timeout=30)

# Determina extensión automáticamente (jpg, mp4, etc.)
content_type = response.headers.get('content-type')
ext = mimetypes.guess_extension(content_type)
```

### 3. Subir a Supabase Storage

```python
# Path: {nombre_nora}/publicaciones_meta/{post_id}.ext
storage_path = f"{nombre_nora}/publicaciones_meta/{filename}"

# Sube con upsert (idempotencia)
supabase.storage.from_('meta-webhooks').upload(
    path=storage_path,
    file=content,
    file_options={"upsert": "true"}
)
```

### 4. Actualizar Base de Datos

**Para fotos:**
```sql
UPDATE meta_publicaciones_webhook SET
    imagen_local = 'https://...supabase.co/storage/.../file.jpg',
    imagen_descargada_en = NOW(),
    procesada = TRUE
WHERE post_id = '...'
```

**Para videos:**
```sql
UPDATE meta_publicaciones_webhook SET
    video_local = 'https://...supabase.co/storage/.../file.mp4',
    video_url_public = 'https://...supabase.co/storage/.../file.mp4',
    video_storage_path = 'nora/publicaciones_meta/file.mp4',
    video_descargado_en = NOW(),
    procesada = TRUE
WHERE post_id = '...'
```

## 🗂️ Estructura de Archivos

### Archivos Creados

```
src/automation_hub/
├── jobs/
│   └── meta_media_download_daily.py          # Job principal
└── integrations/
    └── meta_ads/
        └── media_downloader.py                # Servicio de descarga

migrations/
├── add_meta_media_download_job.sql           # Configuración del job
└── add_video_fields_meta_publicaciones.sql   # Campos de video

probar_meta_media_download.py                  # Script de prueba
```

## 🚀 Uso

### Ejecución Manual

```bash
# Activar entorno virtual
.venv\Scripts\Activate.ps1

# Ejecutar job
python probar_meta_media_download.py
```

### Ejecución Automática

El job se ejecuta automáticamente cada 15 minutos a través del sistema de jobs.

### Verificar Estado

```python
from automation_hub.db.supabase_client import create_client_from_env

supabase = create_client_from_env()

# Ver publicaciones pendientes
pendientes = supabase.table('meta_publicaciones_webhook') \
    .select('*') \
    .not_.is_('imagen_url', 'null') \
    .is_('imagen_local', 'null') \
    .execute()

print(f"Pendientes: {len(pendientes.data)}")
```

## 📁 Campos de la Tabla

### `meta_publicaciones_webhook`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `imagen_url` | text | URL original de Facebook/Instagram |
| `imagen_local` | text | URL pública en Supabase Storage (fotos) |
| `imagen_descargada_en` | timestamp | Cuándo se descargó la imagen |
| `video_local` | text | URL pública en Supabase Storage (videos) |
| `video_url_public` | text | Alias de video_local |
| `video_storage_path` | text | Ruta en el bucket (ej: `nora/publicaciones_meta/123.mp4`) |
| `video_descargado_en` | timestamp | Cuándo se descargó el video |
| `procesada` | boolean | Si ya fue procesada |
| **`media_status`** | **text** | **Estado: `pending`, `downloading`, `success`, `error`** |
| **`media_attempts`** | **integer** | **Número de intentos (0-5)** |
| **`media_last_error`** | **jsonb** | **Último error: `{message, type, timestamp, attempt}`** |
| **`media_updated_at`** | **timestamp** | **Última actualización de media** |

## ⚙️ Configuración de Storage

### Bucket: `meta-webhooks`

**Estructura de directorios:**
```
meta-webhooks/
└── {nombre_nora}/
    └── publicaciones_meta/
        ├── 123456_789012.jpg
        ├── 123456_789013.mp4
        └── ...
```

**Políticas de acceso:**
- Público: Lectura (GET)
- Autenticado: Escritura (POST/PUT)

## 🔍 Monitoreo

### Métricas Clave

El job reporta:
- ✅ **Procesadas:** Total de publicaciones procesadas
- ✅ **Exitosas:** Descargas exitosas
- ❌ **Errores:** Fallos en descarga o almacenamiento

### Alertas

Se crean alertas automáticas si:
- Tasa de error > 20%
- Error crítico en ejecución del job

## 🛡️ Manejo de Errores

### Idempotencia

Si un archivo ya existe en Storage (error 409), se considera éxito:

```python
if '409' in error or 'already exists' in error:
    logger.info("Archivo ya existe (idempotencia)")
    # Continuar normalmente
```

### Tipos de Error

| Error | Retriable | Acción |
|-------|-----------|--------|
| Timeout (>30s) | ⚠️ Advertencia | Log warning |
| HTTP 4xx | ❌ No retriable | Log warning |
| HTTP 5xx | ✅ Retriable | Siguiente ejecución |
| Storage full | ❌ Crítico | Crear alerta |

### Exclusiones

❌ **NO se procesan:**
- Stories/historias (videos sin `mensaje`)
- Publicaciones sin `imagen_url`
- Publicaciones ya descargadas

## 🧪 Testing

### Caso 1: Publicación con Foto

```python
# Crear publicación de prueba
supabase.table('meta_publicaciones_webhook').insert({
    'post_id': 'test_photo_123',
    'page_id': '123456789',
    'tipo_item': 'photo',
    'imagen_url': 'https://scontent.fgdl1-1.fna.fbcdn.net/v/...',
    'mensaje': 'Post de prueba',
    'nombre_nora': 'test_tenant',
    'procesada': False
}).execute()

# Ejecutar job
run()

# Verificar resultado
pub = supabase.table('meta_publicaciones_webhook') \
    .select('imagen_local') \
    .eq('post_id', 'test_photo_123') \
    .single() \
    .execute()

assert 'supabase.co/storage' in pub.data['imagen_local']
```

### Caso 2: Publicación con Video

```python
# Similar al caso 1 pero con tipo_item='video'
# Verificar que video_local esté poblado
```

## 📈 Rendimiento

### Capacidad

- **50 publicaciones/15 min** = 200 publicaciones/hora
- **4,800 publicaciones/día** (24h continuo)
- Ajustable modificando `BATCH_SIZE`

### Optimizaciones

1. **Índices de BD:** `idx_meta_pub_tipo_pendiente` acelera queries
2. **Upsert en Storage:** Evita duplicados sin errores
3. **Filtrado eficiente:** Excluye stories en query, no en código

## 🔗 Integración

### Jobs Relacionados

- **`meta_to_gbp_daily`:** Usa `imagen_local`/`video_local` para publicar en GBP
- **Webhooks Meta:** Pueblan `meta_publicaciones_webhook` con `imagen_url`

### Dependencias

```python
# requirements.txt
requests>=2.31.0
supabase>=2.0.0
```

## 📝 Notas

- URLs de Supabase Storage son públicas y permanentes
- Archivos se nombran con `post_id` para unicidad
- Content-type se detecta automáticamente de headers HTTP
- Extensión fallback: `.jpg` (fotos), `.mp4` (videos)

## 🚨 Troubleshooting

### "Variables de Supabase faltantes"

```bash
# Asegúrate de tener .env con:
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
```

### "No hay publicaciones pendientes"

```sql
-- Verificar que hay publicaciones con imagen_url
SELECT COUNT(*) FROM meta_publicaciones_webhook
WHERE imagen_url IS NOT NULL
AND imagen_local IS NULL;
```

### "Bucket no existe"

```python
# Crear bucket en Supabase Dashboard
# Storage > New Bucket > "meta-webhooks" (public)
```

## 🔄 Migraciones Requeridas

Ejecutar en orden:

1. `add_video_fields_meta_publicaciones.sql` - Agregar campos de video
2. `add_meta_media_download_job.sql` - Configurar job

```bash
# Aplicar migraciones en Supabase SQL Editor
```
