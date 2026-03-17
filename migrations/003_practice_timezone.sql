-- 003_practice_timezone.sql
-- Add timezone column to practices table.
-- Working hours and patient-facing times are interpreted in this timezone.
-- DB storage remains UTC (TIMESTAMPTZ); conversion happens at the application boundary.
--
-- NOTE: After running this migration, re-seed the database so appointment times
-- are stored correctly in UTC (previously they were treated as UTC directly).

ALTER TABLE practices
    ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'America/Los_Angeles';
