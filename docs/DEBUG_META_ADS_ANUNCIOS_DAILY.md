# Debug: meta_ads.anuncios.daily

## 🔍 Análisis del Job Paso por Paso

### Archivo
`src/automation_hub/jobs/meta_ads_anuncios_daily.py`

---

## 📋 Flujo de Ejecución

### **PASO 1: Inicialización**
```python
fecha = date.today() - timedelta(days=2)  # ⚠️ ANTIER (2 días atrás)
```

**❌ PROBLEMA IDENTIFICADO:**
- El job sincroniza datos de hace 2 días (`antier`)
- Línea 251: `fecha = date.today() - timedelta(days=2)`
- **Debería sincronizar AYER** (`days=1`)

**Impacto:**
- Hoy es 2025-12-22
- El job sincroniza: 2025-12-20
- Datos de ayer (2025-12-21): **NO SE SINCRONIZAN**

---

### **PASO 2: Obtener Cuentas Activas**
```python
response = supabase.table('meta_ads_cuentas') \
    .select('id_cuenta_publicitaria,nombre_cuenta,nombre_nora,empresa_id') \
    .eq('activo', True) \
    .execute()
```

✅ **Funciona correctamente**
- Filtra cuentas activas (`activo = True`)
- Obtiene 90 cuentas activas según verificación

---

### **PASO 3: Sincronizar Cada Cuenta**
```python
for cuenta in cuentas:
    result = service.sync_account_daily(
        account_id=account_id,
        fecha_reporte=fecha,  # ⚠️ Usando fecha de hace 2 días
        nombre_nora=nombre
    )
```

**Proceso:**
1. Llama a `MetaAdsDailySyncService.sync_account_daily()`
2. Descarga insights de Meta Ads API
3. Guarda en tabla `meta_ads_anuncios_daily`

**⚠️ Posibles Problemas:**
- ¿Qué hace `MetaAdsDailySyncService`?
- ¿Maneja errores de API correctamente?
- ¿Tiene rate limits?

---

### **PASO 4: Obtener Anuncios Sincronizados**
```python
response = supabase.table('meta_ads_anuncios_daily') \
    .select('...') \
    .eq('fecha_reporte', str(fecha))  # Busca solo la fecha sincronizada
    .execute()
```

✅ **Funciona correctamente**
- Obtiene anuncios de la fecha especificada
- Usa columna correcta: `fecha_reporte` (date)

---

### **PASO 5: Analizar Rendimiento**
```python
for anuncio in anuncios:
    estado, score = analizar_rendimiento_anuncio(anuncio)
    # Clasifica: excelente, bueno, malo, sin_datos
```

**Criterios:**
- **CTR**: >2% excelente, 1-2% bueno, <1% malo
- **CPC**: <$0.50 excelente, $0.50-$1 bueno, >$1 malo
- **Alcance**: >1000 excelente, 500-1000 bueno, <500 malo
- **Engagement**: clicks/alcance

✅ **Lógica correcta**

---

### **PASO 6: Detectar Alertas**

#### 6.1 Cuentas sin anuncios
```python
for cuenta in cuentas:
    if cuenta_id not in anuncios_por_cuenta:
        cuentas_sin_anuncios.append(...)
```

✅ Detecta cuentas que no tienen anuncios en la fecha

#### 6.2 Cuentas con 1 solo anuncio
```python
if len(ads) == 1:
    cuentas_un_anuncio.append(...)
```

✅ Detecta cuentas con pocos anuncios activos

#### 6.3 Anuncios con mal rendimiento
```python
if estado == 'malo':
    anuncios_malos.append(anuncio)
```

✅ Identifica anuncios de bajo rendimiento

---

### **PASO 7: Generar Reporte Telegram**
```python
mensaje = generar_mensaje_telegram(
    fecha=fecha,
    total_cuentas=len(cuentas),
    total_anuncios=total_anuncios,
    ...
)
```

**Contenido:**
- 📊 Resumen general
- ⚠️ Cuentas sin anuncios
- ⚡ Cuentas con 1 solo anuncio
- 🔴 Anuncios con mal rendimiento
- 🏆 TOP 3 mejores anuncios

✅ **Formato correcto**

---

### **PASO 8: Enviar Notificación**
```python
enviado = telegram.enviar_mensaje(mensaje)
```

**⚠️ Verificar:**
- ¿Está configurado `TelegramNotifier`?
- ¿Tiene chat_id correcto?
- ¿Token de bot válido?

---

## 🐛 PROBLEMAS IDENTIFICADOS

### ❌ **PROBLEMA PRINCIPAL: Fecha incorrecta**

**Línea 251:**
```python
fecha = date.today() - timedelta(days=2)  # ❌ ANTIER
```

**Solución:**
```python
fecha = date.today() - timedelta(days=1)  # ✅ AYER
```

**Razón:**
- Meta Ads API proporciona datos con 1 día de retraso
- No con 2 días de retraso
- Por eso no hay datos del 2025-12-21

---

### ⚠️ **PROBLEMA SECUNDARIO: Job no se ejecuta**

**Verificación del script muestra:**
```
✅ meta_ads.anuncios.daily
   ⚠️  Nunca ejecutado
```

**Verificar:**
1. ¿El job está en `registry.py`?
2. ¿El scheduler lo detecta?
3. ¿Hay errores en Railway logs?

---

### ⚠️ **PROBLEMA TERCIARIO: Dependencias**

**Revisar:**
- `MetaAdsDailySyncService` - ¿funciona correctamente?
- ¿Maneja rate limits de Meta Ads API?
- ¿Guarda correctamente en Supabase?

---

## ✅ SOLUCIONES

### 1. **Cambiar fecha de sincronización**

**Archivo:** `src/automation_hub/jobs/meta_ads_anuncios_daily.py`

**Línea 251:**
```python
# ANTES
fecha = date.today() - timedelta(days=2)

# DESPUÉS
fecha = date.today() - timedelta(days=1)
```

---

### 2. **Verificar registro del job**

**Archivo:** `src/automation_hub/jobs/registry.py`

Verificar que incluya:
```python
from automation_hub.jobs import meta_ads_anuncios_daily

JOBS = {
    ...
    "meta_ads.anuncios.daily": meta_ads_anuncios_daily,
    ...
}
```

---

### 3. **Ejecutar job manualmente para probar**

```bash
python -m automation_hub.jobs.meta_ads_anuncios_daily
```

Revisar logs para identificar errores.

---

### 4. **Verificar en Railway**

```bash
# Ver logs del scheduler
railway logs

# Buscar:
# - "meta_ads.anuncios.daily"
# - Errores de importación
# - Errores de ejecución
```

---

## 📊 Estado Actual

| Aspecto | Estado | Detalles |
|---------|--------|----------|
| **Código** | ⚠️ | Fecha incorrecta (antier en vez de ayer) |
| **Ejecución** | ❌ | Nunca se ha ejecutado según jobs_config |
| **Datos en BD** | ⚠️ | Última sincronización: 2025-12-20 |
| **Datos esperados** | ❌ | Datos de ayer (2025-12-21): 0 registros |
| **Telegram** | ❓ | No se ha enviado notificación |

---

## 🎯 Próximos Pasos

1. ✅ **Corregir fecha:** `days=1` en lugar de `days=2`
2. ⚠️ **Verificar registry.py** - que el job esté registrado
3. ⚠️ **Ejecutar manualmente** - probar el job completo
4. ⚠️ **Revisar logs Railway** - buscar errores de ejecución
5. ⚠️ **Verificar MetaAdsDailySyncService** - que funcione correctamente

---

## 🔗 Archivos Relacionados

- `src/automation_hub/jobs/meta_ads_anuncios_daily.py` - Job principal
- `src/automation_hub/jobs/registry.py` - Registro de jobs
- `src/automation_hub/integrations/meta_ads/daily_sync_service.py` - Servicio de sincronización
- `migrations/add_meta_ads_anuncios_daily_job.sql` - Migración de tabla
- `sql/create_meta_ads_anuncios_daily.sql` - Schema de tabla
