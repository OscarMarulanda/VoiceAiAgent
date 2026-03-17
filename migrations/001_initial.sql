-- 001_initial.sql
-- Initial schema for the AI Voice & Chat Agent

-- Practice information
CREATE TABLE IF NOT EXISTS practices (
    id TEXT PRIMARY KEY DEFAULT 'default',
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    website TEXT,
    practice_type TEXT,
    hours JSONB NOT NULL DEFAULT '{}'
);

-- Providers (doctors, hygienists, etc.)
CREATE TABLE IF NOT EXISTS providers (
    id TEXT PRIMARY KEY,
    practice_id TEXT NOT NULL REFERENCES practices(id),
    name TEXT NOT NULL,
    specialty TEXT NOT NULL,
    available_days TEXT[] NOT NULL,
    working_hours JSONB NOT NULL DEFAULT '{}'
);

-- Appointment types and their durations per provider
CREATE TABLE IF NOT EXISTS appointment_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    provider_id TEXT NOT NULL REFERENCES providers(id)
);

-- Insurance plans accepted
CREATE TABLE IF NOT EXISTS insurance_plans (
    id SERIAL PRIMARY KEY,
    practice_id TEXT NOT NULL REFERENCES practices(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL
);

-- Patients
CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Appointments
CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    practice_id TEXT NOT NULL REFERENCES practices(id),
    patient_id INTEGER REFERENCES patients(id),
    patient_name TEXT NOT NULL,
    patient_phone TEXT NOT NULL,
    provider_id TEXT NOT NULL REFERENCES providers(id),
    appointment_type TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    reason TEXT,
    notes TEXT,
    booked_via TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for conflict detection: find overlapping appointments per provider
CREATE INDEX IF NOT EXISTS idx_appointments_provider_time
    ON appointments(provider_id, starts_at)
    WHERE status = 'confirmed';

-- Index for patient lookup
CREATE INDEX IF NOT EXISTS idx_appointments_patient_phone
    ON appointments(patient_phone);

CREATE INDEX IF NOT EXISTS idx_appointments_patient_name
    ON appointments(patient_name);

-- Sessions (voice calls and chat sessions)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    language TEXT DEFAULT 'en',
    caller_number TEXT,
    practice_id TEXT NOT NULL REFERENCES practices(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

-- Conversation messages within a session
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session
    ON messages(session_id, timestamp);
