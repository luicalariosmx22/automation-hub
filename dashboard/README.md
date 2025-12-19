# 🎛️ Dashboard de Gestión de Jobs

Dashboard web local para gestionar los jobs de automation-hub.

## 🚀 Uso

1. Abre `jobs-manager.html` en tu navegador
2. Ingresa tu Supabase URL y Anon Key
3. Haz clic en "Conectar"

## ✨ Funcionalidades

### Ver Jobs
- Lista de todos los jobs configurados
- Estado (Activo/Inactivo)
- Última y próxima ejecución
- Intervalo de ejecución
- Errores recientes (si los hay)

### Gestionar Jobs

**Pausar/Activar:**
- Botón "Pausar" para deshabilitar un job
- Botón "Activar" para habilitar un job pausado

**Ejecutar Inmediatamente:**
- Botón "▶ Ejecutar" programa el job para la próxima corrida del cron
- Establece `next_run_at = NOW()`

**Cambiar Intervalo:**
- Botón "⚙️ Intervalo" para modificar frecuencia
- Opciones: 10min, 30min, 1h, 3h, 6h, 12h, 24h
- O ingresa minutos personalizados

### Agregar Nuevos Jobs
- Botón "➕ Agregar Job" (próximamente)
- Definir nombre e intervalo
- Se crea habilitado por default

## 🔒 Seguridad

- Las credenciales se guardan en localStorage del navegador
- Se usa la Anon Key de Supabase (permisos limitados)
- No se exponen credenciales en el código

## 📝 Notas

- El dashboard se conecta directamente a Supabase
- No requiere servidor backend
- Funciona 100% en el navegador
- Compatible con Chrome, Firefox, Safari, Edge

## 🎨 Interfaz

- Diseño limpio con Tailwind CSS
- Responsive (funciona en móvil)
- Actualización en tiempo real
- Indicadores visuales de estado
