-- 005_session_metrics.sql
-- Add metrics JSONB column to sessions for storing per-session performance data.
-- Stores: total_turns, avg_agent_ms, avg_total_turn_ms, tools_used,
--         appointment_booked, outcome, etc.

ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS metrics JSONB NOT NULL DEFAULT '{}';
