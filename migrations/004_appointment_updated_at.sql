-- 004_appointment_updated_at.sql
-- Add updated_at column to appointments for tracking reschedules and modifications

ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Backfill existing rows: set updated_at = created_at
UPDATE appointments SET updated_at = created_at WHERE updated_at = NOW();

-- Auto-update trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
