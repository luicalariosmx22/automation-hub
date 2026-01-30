-- Agregar soporte para horarios específicos en jobs_config
-- Permite ejecutar jobs a una hora fija del día (ej: 9 AM todos los días)

-- 1. Agregar columna schedule_time (hora del día en formato HH:MM)
ALTER TABLE jobs_config 
ADD COLUMN IF NOT EXISTS schedule_time TIME;

-- 2. Modificar función para calcular next_run_at considerando schedule_time
CREATE OR REPLACE FUNCTION update_next_run_at()
RETURNS TRIGGER AS $$
DECLARE
  next_execution TIMESTAMPTZ;
  time_today TIMESTAMPTZ;
  time_tomorrow TIMESTAMPTZ;
BEGIN
  -- Si tiene schedule_time definido, calcular próxima ejecución a esa hora
  IF NEW.schedule_time IS NOT NULL THEN
    -- Combinar fecha actual con la hora programada (en UTC)
    time_today := (CURRENT_DATE + NEW.schedule_time) AT TIME ZONE 'UTC';
    time_tomorrow := ((CURRENT_DATE + INTERVAL '1 day') + NEW.schedule_time) AT TIME ZONE 'UTC';
    
    -- Si ya pasó la hora de hoy, programar para mañana
    IF NEW.last_run_at IS NULL OR NOW() >= time_today THEN
      NEW.next_run_at := time_tomorrow;
    ELSE
      NEW.next_run_at := time_today;
    END IF;
    
  -- Si NO tiene schedule_time, usar intervalo (comportamiento anterior)
  ELSIF NEW.last_run_at IS NOT NULL THEN
    NEW.next_run_at := NEW.last_run_at + (NEW.schedule_interval_minutes || ' minutes')::INTERVAL;
  END IF;
  
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Actualizar job de calendar.daily.summary para ejecutar a las 4 PM UTC (9 AM Hermosillo)
-- Hermosillo está en UTC-7, entonces 9 AM Hermosillo = 4 PM UTC (16:00)
UPDATE jobs_config
SET 
  schedule_time = '16:00:00'::TIME,
  schedule_interval_minutes = NULL,
  next_run_at = ((CURRENT_DATE + INTERVAL '1 day') + TIME '16:00:00') AT TIME ZONE 'UTC'
WHERE job_name = 'calendar.daily.summary';

-- Comentario
COMMENT ON COLUMN jobs_config.schedule_time IS 'Hora específica del día (UTC) para ejecutar el job. Si está definido, ignora schedule_interval_minutes';
