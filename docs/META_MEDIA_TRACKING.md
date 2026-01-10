# ✅ Job Meta Media Download - Mejoras Implementadas

## 🎯 Tracking Completo de Estado

El job ahora usa todos los campos de tracking disponibles en `meta_publicaciones_webhook`:

### Campos Utilizados

| Campo | Uso | Valores |
|-------|-----|---------|
| `media_status` | Estado actual del proceso | `pending`, `downloading`, `success`, `error` |
| `media_attempts` | Número de intentos realizados | 0-5 |
| `media_last_error` | Último error ocurrido (JSONB) | `{message, type, timestamp, attempt}` |
| `media_updated_at` | Última actualización de media | Timestamp UTC |

---

## 🔄 Flujo con Tracking

### 1. **Estado Inicial** → `pending`
Publicación recién creada por webhook, sin procesar.

### 2. **Descargando** → `downloading`
```python
media_status = 'downloading'
media_updated_at = NOW()
```

### 3. **Exitoso** → `success`
```python
media_status = 'success'
imagen_local = 'https://...supabase.co/storage/.../file.jpg'
media_updated_at = NOW()
media_last_error = NULL  # Limpiar errores previos
```

### 4. **Error** → `pending` (retry) o `error` (final)

**Si `media_attempts < 5`:**
```python
media_status = 'pending'  # Reintentar en próxima ejecución
media_attempts = media_attempts + 1
media_last_error = {
    "message": "Timeout descargando photo (>30s)",
    "type": "timeout",
    "timestamp": "2026-01-07T10:30:45.123Z",
    "attempt": 3
}
media_updated_at = NOW()
```

**Si `media_attempts >= 5`:**
```python
media_status = 'error'  # No reintentar más
media_attempts = 5
media_last_error = {...}
```

---

## 🛡️ Tipos de Error Tracked

| Tipo | Código | Retriable |
|------|--------|-----------|
| `timeout` | Timeout >30s | ✅ Sí |
| `http_error` | 4xx, 5xx | ✅ Sí |
| `storage_error` | Error subiendo a Storage | ✅ Sí |

---

## 📊 Monitoreo de Estado

### Query: Publicaciones por Estado

```sql
SELECT 
    media_status,
    COUNT(*) as total,
    AVG(media_attempts) as avg_intentos
FROM meta_publicaciones_webhook
WHERE imagen_url IS NOT NULL
GROUP BY media_status;
```

**Resultado esperado:**
```
media_status | total | avg_intentos
-------------|-------|-------------
success      | 450   | 1.2
pending      | 5     | 2.4
error        | 2     | 5.0
downloading  | 0     | 1.0
```

### Query: Publicaciones con Errores

```sql
SELECT 
    post_id,
    tipo_item,
    media_attempts,
    media_last_error->>'message' as error_msg,
    media_last_error->>'type' as error_type,
    media_updated_at
FROM meta_publicaciones_webhook
WHERE media_status = 'error'
ORDER BY media_updated_at DESC
LIMIT 10;
```

### Query: Reintentos en Curso

```sql
SELECT 
    post_id,
    tipo_item,
    media_attempts,
    media_last_error->>'message' as ultimo_error,
    media_updated_at
FROM meta_publicaciones_webhook
WHERE media_status = 'pending'
  AND media_attempts > 0
  AND imagen_url IS NOT NULL
ORDER BY media_attempts DESC, media_updated_at ASC;
```

---

## 🔍 Logs Mejorados

### Antes:
```
🔄 Procesando publicación #123: photo - post=456_789
⚠️ Pub #123: Error - Timeout descargando photo (>30s)
```

### Ahora:
```
🔄 Procesando publicación #123: photo - post=456_789 (intento 3/5)
⚠️ Timeout descargando photo (>30s)
🔄 Post 456_789 reintentará (intento 3/5)
```

```
# Al alcanzar máximo:
❌ Post 456_789 alcanzó máximo de intentos (5)
```

---

## 🚨 Alertas Automáticas

El job NO crea alertas por publicaciones individuales (para evitar spam), pero sí alerta si:

- **Tasa de error > 20%** en un batch
- **Error crítico** en ejecución del job

---

## 📈 Ventajas del Tracking

### ✅ **Visibilidad Total**
- Ver estado de cada publicación en tiempo real
- Identificar problemas recurrentes
- Auditoría completa de intentos

### ✅ **Reintentos Inteligentes**
- Máximo 5 intentos automáticos
- No reprocesa publicaciones exitosas
- Evita loops infinitos

### ✅ **Debugging Simplificado**
```python
# Ver último error de una publicación
pub = supabase.table('meta_publicaciones_webhook') \
    .select('media_last_error') \
    .eq('post_id', '123_456') \
    .single().execute()

print(pub.data['media_last_error'])
# {
#   "message": "Timeout descargando photo (>30s)",
#   "type": "timeout",
#   "timestamp": "2026-01-07T10:30:45.123Z",
#   "attempt": 3
# }
```

### ✅ **Limpieza Automática**
- `media_last_error = NULL` al tener éxito
- Errores históricos quedan en logs

---

## 🧪 Testing

### Simular Error
```python
# Forzar timeout en una publicación
supabase.table('meta_publicaciones_webhook').update({
    'imagen_url': 'https://httpstat.us/504?sleep=60000',  # Timeout garantizado
    'media_status': 'pending',
    'media_attempts': 0
}).eq('post_id', 'test_timeout').execute()

# Ejecutar job
run()

# Verificar estado
pub = supabase.table('meta_publicaciones_webhook') \
    .select('*').eq('post_id', 'test_timeout').single().execute()

assert pub.data['media_status'] == 'pending'
assert pub.data['media_attempts'] == 1
assert pub.data['media_last_error']['type'] == 'timeout'
```

### Simular Éxito tras Reintentos
```python
# Publicación con 2 intentos previos fallidos
supabase.table('meta_publicaciones_webhook').update({
    'imagen_url': 'https://valid-image.jpg',  # URL válida ahora
    'media_status': 'pending',
    'media_attempts': 2,
    'media_last_error': {'message': 'Old error', 'type': 'http_error'}
}).eq('post_id', 'test_retry').execute()

# Ejecutar job
run()

# Verificar que limpió errores
pub = supabase.table('meta_publicaciones_webhook') \
    .select('*').eq('post_id', 'test_retry').single().execute()

assert pub.data['media_status'] == 'success'
assert pub.data['imagen_local'] is not None
assert pub.data['media_last_error'] is None  # ✅ Limpiado
```

---

## 📋 Checklist de Implementación

- [x] Agregar función `_registrar_error()`
- [x] Actualizar `descargar_media_desde_url()` para usar tracking
- [x] Actualizar `get_publicaciones_pendientes()` con filtros de estado
- [x] Mejorar logs con número de intento
- [x] Limpiar `media_last_error` en éxito
- [x] Marcar como `downloading` antes de subir
- [x] Limitar reintentos a MAX_ATTEMPTS (5)
- [x] Documentar queries de monitoreo

---

## 🎯 Próximos Pasos

1. **Ejecutar migración:**
   ```sql
   -- migrations/add_meta_media_download_job.sql
   ```

2. **Probar job:**
   ```bash
   python probar_meta_media_download.py
   ```

3. **Monitorear primeras ejecuciones:**
   ```sql
   SELECT media_status, COUNT(*) 
   FROM meta_publicaciones_webhook 
   GROUP BY media_status;
   ```

4. **Ajustar MAX_ATTEMPTS si es necesario** (actualmente 5)

---

## 📞 Soporte

Si ves muchas publicaciones en estado `error`:
1. Revisar `media_last_error` para patrones comunes
2. Verificar conectividad con Facebook
3. Verificar bucket de Supabase Storage
4. Considerar aumentar `TIMEOUT_SECONDS` (actualmente 30s)
