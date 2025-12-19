# Meta Ads - Job de Cuentas Publicitarias

Job para sincronizar información de cuentas publicitarias de Meta Ads.

## 🎯 Funcionalidad

Este job actualiza automáticamente la información de todas las cuentas publicitarias activas en la tabla `meta_ads_cuentas`.

### Datos que sincroniza:

- ✅ **Estado de la cuenta** (`account_status`)
- ✅ **Nombre de la cuenta** (`nombre_cliente`)
- ✅ **Anuncios activos** (`ads_activos`)
- ✅ **Gasto del mes** (`gasto_actual_mes`)
- ✅ **Estado de conexión** (`conectada`)
- ✅ **Última actualización** (`ultima_notificacion`)
- ⚠️ **Errores de API** (`ultimo_error`, `ultimo_error_at`)

## 🔧 Configuración Requerida

### Variables de Entorno

```bash
# Obligatorio
META_ADS_ACCESS_TOKEN=EAAxxxx...  # Token de acceso de Meta Ads

# Opcional
META_ADS_NOMBRE_NORA=cliente1     # Filtrar por tenant específico
```

### Obtener Token de Meta Ads

1. Ir a [Meta for Developers](https://developers.facebook.com/)
2. Crear una app o usar una existente
3. Agregar permisos: `ads_read`, `ads_management`
4. Generar token de acceso de larga duración
5. Configurar en Railway/variables de entorno

## 📊 Información de la API

**API utilizada:** Meta Graph API v18.0

**Endpoints:**
- `GET /{ad-account-id}` - Información de la cuenta
- `GET /{ad-account-id}/ads` - Anuncios activos

**Campos obtenidos:**
```json
{
  "name": "Nombre de la cuenta",
  "account_status": 1,
  "currency": "MXN",
  "amount_spent": 150000,
  "ads_activos": 5
}
```

## 🚀 Ejecución

### Manual (local)
```bash
PYTHONPATH=src python -m automation_hub.runners.run_job meta_ads.cuentas.daily
```

### Automático (Railway)
Ejecutar SQL en Supabase:
```sql
-- Agregar a jobs_config
\i migrations/add_meta_ads_cuentas_job.sql

-- Verificar
SELECT * FROM jobs_config WHERE job_name = 'meta_ads.cuentas.daily';
```

El job se ejecutará automáticamente cada 24 horas.

## 📝 Logs Esperados

**Ejecución exitosa:**
```
2025-12-19 10:00:00 - INFO - Iniciando job: meta_ads.cuentas.daily
2025-12-19 10:00:00 - INFO - Obteniendo cuentas publicitarias activas
2025-12-19 10:00:00 - INFO - Procesando 3 cuentas publicitarias
2025-12-19 10:00:01 - INFO - Procesando cuenta: Mi Negocio - Ads
2025-12-19 10:00:02 - INFO - ✓ Cuenta Mi Negocio - Ads actualizada: 5 anuncios activos
2025-12-19 10:00:05 - INFO - Job meta_ads.cuentas.daily completado
2025-12-19 10:00:05 - INFO -   Total cuentas: 3
2025-12-19 10:00:05 - INFO -   Actualizadas: 3
2025-12-19 10:00:05 - INFO -   Con errores: 0
```

**Con errores:**
```
2025-12-19 10:00:03 - ERROR - ✗ Error procesando cuenta Test Account: Invalid OAuth access token
2025-12-19 10:00:05 - INFO -   Con errores: 1
```

## ⚠️ Manejo de Errores

Cuando una cuenta falla:
- Se marca como `conectada = false`
- Se guarda el error en `ultimo_error` (JSONB)
- Se actualiza `ultimo_error_at`
- Se crea alerta con prioridad **media**
- El job continúa con las siguientes cuentas

## 🎨 Frontend

El dashboard en `/meta_ads/cuentas_publicitarias` mostrará:
- 🟢 Anuncios activos actualizados
- 📅 Última actualización (timestamp)
- ⚠️ Errores de conexión si los hay

## 🔄 Integración

Este job se complementa con:
- `meta_ads.rechazos.daily` - Detecta anuncios rechazados
- Webhooks de Meta Ads - Actualizaciones en tiempo real
- Dashboard de cuentas - Visualización de datos

## 📈 Métricas

El job genera alertas en la tabla `alertas` con:
```json
{
  "total_cuentas": 10,
  "actualizadas": 9,
  "errores": 1,
  "cuentas_con_error": [
    {
      "id": "act_123456",
      "nombre": "Cuenta Test",
      "error": "Invalid OAuth token"
    }
  ]
}
```

## 🛠️ Solución de Problemas

**Error: META_ADS_ACCESS_TOKEN no configurado**
→ Agregar variable de entorno con token de Meta

**Error: Invalid OAuth access token**
→ Token expirado, regenerar en Meta for Developers

**Error: No se encontraron cuentas activas**
→ Verificar que existan cuentas con `activo = true` en la tabla

**Error: Permission denied**
→ Asegurar que el token tenga permisos `ads_read`
