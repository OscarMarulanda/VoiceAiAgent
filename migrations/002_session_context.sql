-- 002_session_context.sql
-- Add JSONB context column to sessions for notepad-style conversation state.
-- Stores structured patient info, tool call log, and soft context notes
-- so the agent doesn't need full conversation history every turn.

ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS context JSONB NOT NULL DEFAULT '{}';
