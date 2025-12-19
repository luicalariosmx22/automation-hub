-- Tabla para configuración y tracking de jobs
CREATE TABLE IF NOT EXISTS jobs_config (
  job_name TEXT PRIMARY KEY,
  enabled BOOLEAN DEFAULT true,
  schedule_interval_minutes INTEGER DEFAULT 1440, -- 1440 = 24 horas (diario)
  last_run_at TIMESTAMPTZ,
  next_run_at TIMESTAMPTZ,
  config JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para buscar jobs listos para ejecutar
CREATE INDEX IF NOT EXISTS idx_jobs_config_next_run 
  ON jobs_config(next_run_at) 
  WHERE enabled = true;

-- Función para calcular next_run_at automáticamente
CREATE OR REPLACE FUNCTION update_next_run_at()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.last_run_at IS NOT NULL THEN
    NEW.next_run_at := NEW.last_run_at + (NEW.schedule_interval_minutes || ' minutes')::INTERVAL;
  END IF;
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar next_run_at cuando cambia last_run_at
CREATE TRIGGER trigger_update_next_run_at
  BEFORE UPDATE ON jobs_config
  FOR EACH ROW
  WHEN (OLD.last_run_at IS DISTINCT FROM NEW.last_run_at)
  EXECUTE FUNCTION update_next_run_at();

-- Insertar jobs existentes
INSERT INTO jobs_config (job_name, enabled, schedule_interval_minutes, next_run_at) VALUES
  ('gbp.reviews.daily', true, 1440, NOW()), -- Diario
  ('gbp.metrics.daily', true, 1440, NOW()),
  ('meta_ads.rechazos.daily', true, 1440, NOW())
ON CONFLICT (job_name) DO NOTHING;

-- Comentarios
COMMENT ON TABLE jobs_config IS 'Configuración y estado de ejecución de jobs automatizados';
COMMENT ON COLUMN jobs_config.schedule_interval_minutes IS 'Intervalo de ejecución en minutos (1440 = diario, 60 = cada hora)';
COMMENT ON COLUMN jobs_config.last_run_at IS 'Última vez que se ejecutó el job exitosamente';
COMMENT ON COLUMN jobs_config.next_run_at IS 'Próxima ejecución programada (calculada automáticamente)';
