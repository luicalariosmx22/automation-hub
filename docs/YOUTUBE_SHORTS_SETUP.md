# Integración con YouTube Shorts

## 📋 Descripción

Esta integración permite subir videos automáticamente a YouTube Shorts desde las publicaciones de Facebook.

**IMPORTANTE:** Solo el **OWNER (propietario)** del canal de YouTube puede conectar la integración. Los permisos de Manager o Editor en YouTube Studio **NO funcionan** con las APIs de YouTube.

## 🔑 Configuración en Google Cloud Console

### 1. Crear Proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita **YouTube Data API v3**:
   - APIs & Services > Library
   - Busca "YouTube Data API v3"
   - Click en "Enable"

### 2. Crear Credenciales OAuth 2.0

1. Ve a **APIs & Services > Credentials**
2. Click en **Create Credentials > OAuth client ID**
3. Selecciona **Web application**
4. Configura:
   - **Name**: "Automation Hub - YouTube Integration"
   - **Authorized redirect URIs**:
     - `http://localhost:8000/integraciones/youtube/callback` (desarrollo)
     - `https://tu-dominio.com/integraciones/youtube/callback` (producción)
5. Click en **Create**
6. **Descarga el JSON** de credenciales

### 3. Configurar OAuth Consent Screen

1. Ve a **APIs & Services > OAuth consent screen**
2. Selecciona **External** (o Internal si es Google Workspace)
3. Completa la información:
   - **App name**: "Automation Hub"
   - **User support email**: tu email
   - **Developer contact**: tu email
4. En **Scopes**, agrega:
   - `https://www.googleapis.com/auth/youtube.upload`
5. En **Test users** (si está en modo Testing):
   - Agrega los emails de los propietarios de canales que conectarán

### 4. Configurar en Automation Hub

1. Copia el archivo de credenciales descargado:
   ```bash
   cp Downloads/client_secret_*.json youtube_client_secrets.json
   ```

2. Agrega variable de entorno:
   ```bash
   # .env
   YOUTUBE_CLIENT_SECRETS_FILE=youtube_client_secrets.json
   ```

3. Aplica migración de base de datos:
   ```bash
   # En Supabase SQL Editor
   # Ejecutar: db/migrations/007_youtube_integration.sql
   ```

4. Configura el job:
   ```bash
   # En Supabase SQL Editor
   # Ejecutar: migrations/add_youtube_shorts_job.sql
   ```

## 🔗 Conectar Canal de YouTube

### Desde el código:

```python
from automation_hub.integrations.youtube.youtube_service import YouTubeService
from automation_hub.db.supabase_client import get_supabase_client

supabase = get_supabase_client()
youtube_service = YouTubeService(supabase)

# Generar URL de conexión
auth_url = youtube_service.get_authorization_url(
    cliente_id="uuid-del-cliente",
    redirect_uri="http://localhost:8000/integraciones/youtube/callback"
)

print(f"Ir a: {auth_url}")
```

### Desde la web:

1. Ve a: `http://localhost:8000/integraciones/youtube/connect?cliente_id=UUID`
2. Verás un warning indicando que solo el OWNER puede conectar
3. Click en "Continuar con Google"
4. Inicia sesión con la cuenta **propietaria del canal**
5. Autoriza los permisos de YouTube
6. Serás redirigido al callback que guardará la conexión

### Verificar conexión:

```python
# Listar canales conectados
canales = youtube_service.get_canales_conectados("uuid-del-cliente")

for canal in canales:
    print(f"Canal: {canal['canal_titulo']}")
    print(f"ID: {canal['canal_id']}")
```

## 📤 Subir Videos

### Manual:

```python
resultado = youtube_service.upload_video(
    cliente_id="uuid-del-cliente",
    video_path="/path/to/video.mp4",
    title="Mi video",
    description="Descripción del video",
    tags=["shorts", "automation"],
    privacy_status="public",  # 'public', 'private', 'unlisted'
    validate_shorts=True  # Valida duración <=180s y aspecto vertical
)

print(f"Video subido: {resultado['url']}")
print(f"Es Short: {resultado['is_short']}")
```

### Automático (Job):

El job `youtube_shorts_daily` se ejecuta cada 24 horas y:

1. Busca publicaciones de Facebook con video
2. Filtra las que ya están en GBP (`publicada_gbp = true`)
3. Verifica que el cliente tenga YouTube conectado
4. Descarga el video de Supabase Storage
5. Valida que sea apto para Shorts (<=180s, vertical/cuadrado)
6. Sube a YouTube con `privacy_status = public`
7. Envía notificación por Telegram
8. Limita a 5 videos por ejecución con 2 minutos de delay

## 🎯 Validación de Shorts

YouTube detecta automáticamente si un video es Short basándose en:

- **Duración**: ≤ 60 segundos (tolerancia hasta 180s)
- **Orientación**: Vertical (9:16) o Cuadrada (1:1)

La integración valida estos criterios usando `ffprobe` antes de subir.

## ⚠️ Permisos y Limitaciones

### ✅ Funciona con:
- Cuenta **OWNER** del canal de YouTube
- OAuth 2.0 con scope `youtube.upload`
- Videos en Supabase Storage

### ❌ NO funciona con:
- Cuentas con permisos de **Manager** o **Editor** en YouTube Studio
- Videos alojados en Facebook/Instagram (se descargan de Supabase)
- CMS/Content Partner (requiere configuración especial)

## 🗃️ Estructura de Datos

### Tabla: `youtube_conexiones`

```sql
- id: UUID
- cliente_id: UUID (FK a cliente_empresas)
- canal_id: TEXT (channelId de YouTube)
- canal_titulo: TEXT (nombre del canal)
- refresh_token: TEXT (token persistente)
- access_token: TEXT (cache opcional)
- token_expira_en: TIMESTAMP
- created_at: TIMESTAMP
```

### Tabla: `youtube_videos`

```sql
- id: UUID
- conexion_id: UUID (FK a youtube_conexiones)
- cliente_id: UUID (FK a cliente_empresas)
- video_id: TEXT (ID en YouTube)
- video_url: TEXT (URL pública)
- title, description, tags
- privacy_status: TEXT ('public', 'private', 'unlisted')
- is_short: BOOLEAN
- duration, width, height, aspect_ratio
- source_type, source_id (rastreo de origen)
- uploaded_at: TIMESTAMP
```

## 🚀 Endpoints

### GET `/integraciones/youtube/connect`
Inicia flujo OAuth

**Query params:**
- `cliente_id`: UUID del cliente

**Response:** Página HTML con warning y redirección a Google

### GET `/integraciones/youtube/callback`
Callback de OAuth (automático)

**Query params:**
- `code`: Código de autorización
- `state`: cliente_id original

**Response:** Página HTML de éxito con canal conectado

### POST `/integraciones/youtube/disconnect/<conexion_id>`
Desconecta un canal

**Response:**
```json
{
  "success": true,
  "message": "Canal desconectado"
}
```

### GET `/integraciones/youtube/canales/<cliente_id>`
Lista canales conectados

**Response:**
```json
{
  "success": true,
  "canales": [
    {
      "id": "uuid",
      "canal_id": "UC...",
      "canal_titulo": "Mi Canal",
      "created_at": "2026-01-06T..."
    }
  ]
}
```

## 📊 Monitoreo

### Logs del Job

```bash
# Ver ejecuciones recientes
SELECT 
    job_name,
    started_at,
    finished_at,
    status,
    error_message
FROM job_executions
WHERE job_name = 'youtube_shorts_daily'
ORDER BY started_at DESC
LIMIT 10;
```

### Videos Subidos

```bash
# Últimos videos subidos
SELECT 
    v.video_id,
    v.title,
    v.is_short,
    v.privacy_status,
    v.uploaded_at,
    c.canal_titulo
FROM youtube_videos v
JOIN youtube_conexiones c ON v.conexion_id = c.id
ORDER BY v.uploaded_at DESC
LIMIT 20;
```

## 🔧 Troubleshooting

### Error: "No se encontró un canal asociado"
- Verificar que iniciaste sesión con la cuenta OWNER del canal
- Revisar que el canal esté creado (no solo cuenta de Google)

### Error: "Usuario solo es manager/editor"
- Solo el propietario del canal puede usar APIs
- Pedir al owner que conecte su cuenta

### Error: "Access token expired"
- El sistema automáticamente refresca tokens
- Si persiste, desconectar y reconectar el canal

### Error: "Video no es apto para Shorts"
- Verificar duración ≤ 180 segundos
- Verificar aspect ratio vertical (9:16) o cuadrado (1:1)
- Revisar que el video sea MP4 válido

## 📚 Referencias

- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [OAuth 2.0 para Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [YouTube Shorts Specifications](https://support.google.com/youtube/answer/10059070)
