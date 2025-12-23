# META TO GBP DAILY - Documentación de Implementación

## Objetivo
Crear un job automatizado que publique posts de Facebook con imágenes a Google Business Profile.

## Componentes Implementados

### 1. Integración GBP API (src/automation_hub/integrations/gbp/posts_v1.py)
- **API**: Google My Business v4 LocalPosts endpoint
- **Autenticación**: OAuth 2.0 usando `google.oauth.get_bearer_header()`
- **Función principal**: `create_local_post(location_name, auth_header, summary, media_url)`
- **Formato de media**: `{"mediaFormat": "PHOTO", "sourceUrl": url}`

### 2. Job Principal (src/automation_hub/jobs/meta_to_gbp_daily.py)
```python
def run(ctx=None):
    # 1. Obtener OAuth token
    # 2. Buscar posts pendientes (procesada=False)
    # 3. Para cada post:
    #    - Obtener empresa desde facebook_paginas
    #    - Obtener locaciones GBP de esa empresa
    #    - Publicar en cada locación con imagen
    #    - Marcar como procesada=True
```

### 3. Migración Job Config (migrations/add_meta_to_gbp_job.sql)
```sql
INSERT INTO jobs_config (job_name, enabled, schedule_interval_minutes, next_run_at, config)
VALUES ('meta_to_gbp_daily', true, 1440, NOW(), {...})
```

## Problemas Encontrados y Soluciones

### ❌ Problema 1: API Endpoint Incorrecto
- **Error**: Usar API v1 en lugar de v4
- **Solución**: Cambiar a `https://mybusinessbusinessinformation.googleapis.com/v1/{location_name}/localPosts`

### ❌ Problema 2: Esquema de Base de Datos 
- **Error**: Campos faltantes como `nombre_nora` (NOT NULL)
- **Solución**: Agregar campos requeridos en inserts/updates

### ❌ Problema 3: Accesibilidad de Imágenes
- **Error**: URLs de Facebook CDN no son públicamente accesibles (403)
- **Descubrimiento**: `imagen_local` SÍ es accesible cuando está en el servidor
- **Solución**: Usar `imagen_local` directamente cuando existe

### ❌ Problema 4: Datos de Prueba Incorrectos
- **Error**: Usar empresa/posts antiguos sin imágenes accesibles
- **Solución**: Usar datos reales proporcionados por el usuario:
  - empresa_id: `20048b86-73ad-44b7-8919-18f04d3b452c`
  - post_id: `116707543052879_1485289873600426`
  - imagen_local: `https://app.soynoraai.com/static/uploads/feed_images/aura/2025/12/116707543052879_1485289873600426_1766448032.jpg`

### ❌ Problema 5: Esquema gbp_locations
- **Error**: Campo `is_active` no existe en tabla
- **Solución**: Remover filtro `.eq("is_active", True)` de consultas

## Flujo de Trabajo Final ✅

1. **Webhook recibe post de Facebook** → `meta_publicaciones_webhook`
2. **Sistema descarga imagen** → `imagen_local` (URL accesible)
3. **Job daily se ejecuta** → Busca `procesada=False`
4. **Para cada post pendiente**:
   - Obtiene `empresa_id` desde `facebook_paginas`
   - Obtiene locaciones GBP de esa empresa  
   - Llama a GBP API con `imagen_local` como `sourceUrl`
   - Marca `procesada=True`

## Test de Validación Exitoso

```bash
python scripts/test_post_especifico.py
```

**Resultado**:
```
✅ Post encontrado: 🎄 Aviso importante 🎄...
✅ Imagen: https://app.soynoraai.com/static/uploads/feed_images/aura/2025/12/...
✅ Página: Sin nombre - Empresa: 20048b86-73ad-44b7-8919-18f04d3b452c  
✅ Locación GBP: accounts/104819734010595427113/locations/10311115792833217163
🚀 PUBLICANDO EN GBP...
✅ PUBLICADO EN GBP: {'name': '...localPosts/1557450406629080274', 'media': [{'mediaFormat': 'PHOTO'}]}
✅ Post marcado como procesado
```

## Configuración de Producción

### Variables de Entorno Requeridas
- `GOOGLE_OAUTH_REFRESH_TOKEN`
- `GOOGLE_OAUTH_CLIENT_ID`  
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `SUPABASE_URL`
- `SUPABASE_KEY`

### Cronograma
- **Frecuencia**: Cada 24 horas (1440 minutos)
- **Timeout**: 600 segundos
- **Reintentos**: 2 intentos con delay de 60 segundos

## Estructura de Archivos

```
src/automation_hub/
├── integrations/gbp/posts_v1.py          # API client GBP
├── jobs/meta_to_gbp_daily.py             # Job principal
scripts/
├── test_post_especifico.py               # Test unitario
migrations/
├── add_meta_to_gbp_job.sql               # Registro en jobs_config
```

## Comandos Útiles

```bash
# Test manual
python scripts/test_post_especifico.py

# Resetear post para pruebas
python -c "from automation_hub.db.supabase_client import create_client_from_env; 
           client = create_client_from_env(); 
           client.table('meta_publicaciones_webhook').update({'procesada': False}).eq('post_id', 'POST_ID').execute()"

# Verificar job registrado
SELECT * FROM jobs_config WHERE job_name = 'meta_to_gbp_daily';
```

## Notas Técnicas

1. **Imágenes**: Solo funciona con URLs públicamente accesibles (`imagen_local`)
2. **Empresas**: Requiere configuración previa en `facebook_paginas` y `gbp_locations`  
3. **OAuth**: Token se refresca automáticamente en cada ejecución
4. **Errores**: Se loggean en sistema de alertas con notificaciones Telegram

---
*Implementado: 22 de diciembre de 2025*
*Estado: ✅ FUNCIONAL - Test exitoso con imagen*