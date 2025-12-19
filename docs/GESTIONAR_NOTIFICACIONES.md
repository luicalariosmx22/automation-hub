# 📱 Gestión de Notificaciones por Telegram

## 🎯 Sistema Configurado

Ya tienes el sistema de notificaciones funcionando con:
- ✅ Tabla `notificaciones_telegram_config` creada
- ✅ Todos los jobs envían notificaciones
- ✅ Filtros por cliente, job y prioridad
- ✅ Configuración flexible

## 👥 Agregar Más Destinatarios

### Opción 1: SQL (Directo en Supabase)

```sql
-- Admin que recibe TODO
INSERT INTO notificaciones_telegram_config (
    nombre_nora, 
    chat_id, 
    nombre_contacto
) VALUES (
    'Sistema',
    '5674082622',
    'Luis - Admin'
);

-- Cliente específico - Solo alertas de alta prioridad
INSERT INTO notificaciones_telegram_config (
    nombre_nora, 
    chat_id, 
    nombre_contacto,
    prioridades_permitidas
) VALUES (
    'Marina',
    '1234567890',
    'Marina - Cliente',
    ARRAY['alta']
);

-- Grupo de equipo - Solo jobs de Meta Ads
INSERT INTO notificaciones_telegram_config (
    nombre_nora, 
    chat_id, 
    nombre_contacto,
    jobs_permitidos,
    prioridades_permitidas
) VALUES (
    'Sistema',
    '-987654321',
    'Grupo Meta Ads Team',
    ARRAY['meta_ads.rechazos.daily', 'meta_ads.cuentas.sync.daily'],
    ARRAY['alta', 'media']
);

-- Cliente con jobs específicos
INSERT INTO notificaciones_telegram_config (
    nombre_nora, 
    chat_id, 
    nombre_contacto,
    jobs_permitidos
) VALUES (
    'Carlos',
    '5551234567',
    'Carlos - GBP',
    ARRAY['gbp.reviews.daily', 'gbp.metrics.daily']
);
```

### Opción 2: Python Script

Crea y ejecuta un script para agregar destinatarios:

```python
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.telegram_config_repo import agregar_destinatario_telegram

supabase = create_client_from_env()

# Agregar destinatario
agregar_destinatario_telegram(
    supabase=supabase,
    nombre_nora="Marina",
    chat_id="1234567890",
    nombre_contacto="Marina - Cliente",
    prioridades_permitidas=["alta"],  # Solo alertas críticas
    notas="Cliente VIP - solo urgencias"
)
```

## 📋 Campos de Configuración

| Campo | Descripción | Valores |
|-------|-------------|---------|
| **nombre_nora** | Cliente/Sistema | "Sistema", "Luis", "Marina", etc. |
| **chat_id** | ID de Telegram | Usuario: "123456789", Grupo: "-987654321" |
| **nombre_contacto** | Descriptivo | "Luis - Admin", "Grupo Meta Ads" |
| **jobs_permitidos** | Jobs que notifican | `NULL` = todos, `ARRAY['gbp.reviews.daily']` = solo ese |
| **prioridades_permitidas** | Prioridades | `NULL` = todas, `ARRAY['alta']` = solo alta |
| **tipos_alerta_permitidos** | Tipos específicos | `NULL` = todos, `ARRAY['cuenta_desactivada']` |
| **activo** | ¿Notificar? | `true` / `false` |

## 🔍 Cómo Obtener Chat ID

### Para Usuarios Individuales:

1. Usuario envía mensaje al bot
2. Ejecuta:
   ```bash
   python scripts/setup_telegram_bot.py TU_BOT_TOKEN
   ```
3. Copia el chat_id que aparece

### Para Grupos:

1. Crea el grupo en Telegram
2. Agrega el bot al grupo
3. Hazlo administrador
4. Alguien envía un mensaje en el grupo
5. Ejecuta:
   ```bash
   python scripts/setup_telegram_bot.py TU_BOT_TOKEN
   ```
6. El chat_id del grupo empieza con `-` (ej: `-987654321`)

### Opción Rápida (API):

```bash
# Ver todos los updates
curl "https://api.telegram.org/bot<TU_TOKEN>/getUpdates"
```

## 📊 Ejemplos de Configuración

### Caso 1: Admin que recibe TODO
```sql
INSERT INTO notificaciones_telegram_config 
(nombre_nora, chat_id, nombre_contacto) 
VALUES ('Sistema', '5674082622', 'Admin General');
```
- ✅ Todos los jobs
- ✅ Todas las prioridades
- ✅ Todos los tipos

### Caso 2: Cliente solo alertas críticas
```sql
INSERT INTO notificaciones_telegram_config 
(nombre_nora, chat_id, nombre_contacto, prioridades_permitidas) 
VALUES ('Luis', '1234567890', 'Luis - Cliente', ARRAY['alta']);
```
- ✅ Solo su nombre_nora
- ✅ Solo prioridad "alta"
- ⚠️ Cuentas desactivadas, rechazos, errores críticos

### Caso 3: Equipo Meta Ads
```sql
INSERT INTO notificaciones_telegram_config 
(nombre_nora, chat_id, nombre_contacto, jobs_permitidos, prioridades_permitidas) 
VALUES 
('Sistema', '-100123456789', 'Grupo Meta Ads', 
 ARRAY['meta_ads.rechazos.daily', 'meta_ads.cuentas.sync.daily'], 
 ARRAY['alta', 'media']);
```
- ✅ Solo jobs de Meta Ads
- ✅ Prioridad alta y media
- ℹ️ No recibe jobs de GBP

### Caso 4: Cliente específico con sus jobs
```sql
INSERT INTO notificaciones_telegram_config 
(nombre_nora, chat_id, nombre_contacto, jobs_permitidos) 
VALUES 
('Marina', '9876543210', 'Marina - GBP', 
 ARRAY['gbp.reviews.daily', 'gbp.metrics.daily']);
```
- ✅ Solo jobs de GBP
- ✅ Todas las prioridades
- ℹ️ No recibe alertas de Meta Ads

## 🔧 Gestión de Destinatarios

### Ver todos los destinatarios
```python
from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.db.repositories.telegram_config_repo import fetch_destinatarios_telegram

supabase = create_client_from_env()
destinatarios = fetch_destinatarios_telegram(supabase)

for d in destinatarios:
    print(f"{d['nombre_contacto']}: {d['chat_id']}")
```

### Desactivar un destinatario
```python
from automation_hub.db.repositories.telegram_config_repo import desactivar_destinatario_telegram

desactivar_destinatario_telegram(supabase, config_id=2)
```

### Actualizar configuración
```python
from automation_hub.db.repositories.telegram_config_repo import actualizar_destinatario_telegram

actualizar_destinatario_telegram(
    supabase, 
    config_id=2,
    prioridades_permitidas=['alta']
)
```

## 🧪 Probar Notificaciones

```bash
# Probar configuración completa
python scripts/test_telegram_config.py

# Enviar notificación de prueba específica
python -c "
from automation_hub.integrations.telegram.notifier import notificar_alerta_telegram
notificar_alerta_telegram(
    nombre='Test',
    descripcion='Probando configuración',
    prioridad='alta',
    nombre_nora='Luis',
    job_name='test.job'
)
"
```

## 📝 Jobs Disponibles

Para configurar `jobs_permitidos`, usa estos nombres:

- `gbp.reviews.daily` - Reviews de Google Business Profile
- `gbp.metrics.daily` - Métricas de GBP
- `meta_ads.rechazos.daily` - Anuncios rechazados de Meta
- `meta_ads.cuentas.sync.daily` - Sincronización de cuentas Meta

## ⚡ Prioridades

- **alta** 🚨 - Cuentas desactivadas, anuncios rechazados, errores críticos
- **media** ⚠️ - Advertencias, muchos cambios, resúmenes con problemas
- **baja** ℹ️ - Completación normal de jobs, información

## 🎯 Tipos de Alerta

Para `tipos_alerta_permitidos`:

- `cuenta_desactivada` - Cuentas Meta Ads desactivadas
- `meta_ads_rechazados` - Anuncios rechazados
- `job_completado` - Finalización de jobs
- `test` - Notificaciones de prueba

## 💡 Tips

1. **Grupos mejor que usuarios individuales**: Más fácil gestionar equipo
2. **Sistema siempre debe tener admin**: Al menos un destinatario con todo
3. **Prioridades son tu amigo**: No satures a clientes con todo
4. **Prueba antes de producción**: Usa `test_telegram_config.py`
5. **Desactiva, no elimines**: Mantén historial de configuraciones

## 🚀 Próximos Pasos

1. Decide qué grupos/usuarios necesitas
2. Créalos en Telegram y agrega el bot
3. Obtén sus chat_ids
4. Inserta configuraciones en la tabla
5. Prueba con `test_telegram_config.py`
6. Monitorea primeros días para ajustar filtros
