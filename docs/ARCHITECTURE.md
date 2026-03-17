# Architecture

## System Overview

```
                         ┌──────────────────────────────────────────────────┐
                         │                FastAPI Backend                    │
                         │                                                  │
Patient ──► Twilio ──────┤  ┌──────────┐    ┌───────────┐   ┌───────────┐ │
  (phone)   (voice)      │  │  Voice    │    │           │   │           │ │
                         │  │  Handler  │───►│  Agent    │──►│PostgreSQL │ │
                         │  └──────────┘    │  Core     │   │ (asyncpg) │ │
Patient ──► JS Widget ──┤  ┌──────────┐    │  (Claude  │   │           │ │
  (browser) (WebSocket)  │  │  Chat    │───►│   API +   │   │ sessions  │ │
                         │  │  Handler  │    │   Tools)  │   │ appts     │ │
                         │  └──────────┘    │           │   │ providers │ │
                         │                   │           │   │ patients  │ │
Staff ──► Admin UI ─────┤  ┌──────────┐    │           │   └───────────┘ │
  (browser)              │  │  Admin   │────┘           │                  │
                         │  │  Routes  │                │──► SendGrid     │
                         │  └──────────┘                │    (email)      │
                         │                   └───────────┘                  │
                         └──────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Twilio Voice Gateway
- Receives incoming calls via webhook
- Streams audio to/from our backend
- We use Twilio Media Streams (WebSocket) for real-time audio
- Manages call state (answer, hold, hangup)

### 2. Voice Pipeline (Call Session Pattern — ADR-028)
- Each phone call gets a **CallSession** object that owns the full lifecycle
- CallSession orchestrates: audio in → Deepgram STT → Agent Core → Deepgram Aura-2 TTS → audio back to Twilio
- State per call: `is_speaking` flag, `stream_sid`, Deepgram connection
- Interruption handling: stops TTS when patient speaks (Twilio `clear` event — ADR-026)
- STT and TTS are stateless service wrappers — swappable without touching session logic
- Language detection on first transcript → switches TTS voice model, fillers, farewell messages
- Pre-generated greeting plays instantly on call connect (ADR-027)
- Handles 10-50 concurrent calls per server instance; scales horizontally or via event-driven migration

### 3. Chat Handler (ADR-036)
- WebSocket endpoint (`/chat/ws`) for the embeddable chat widget
- Receives text messages from the browser, passes to Agent Core, returns text responses
- Typing indicator while agent processes
- Application-level ping/pong keepalive (30s interval, 60s timeout)
- Session persistence via `sessionStorage` — survives page navigation
- Auto-reconnect with exponential backoff (1s → 30s, max 10 attempts)
- Widget: single self-contained `widget.js` file, Shadow DOM encapsulated, configurable via data attributes
- Much simpler than voice — no STT/TTS needed

### 4. Agent Core
- The brain of the system
- Uses **Claude API** with **programmatic tool calling**
- Conversation context per turn: structured notepad (JSONB) + compact tool log + last 8 exchanges (NOT full history)
- Tool loop: up to 6 tool calls per user message
- Has access to 9 tools:
  - `check_availability` — Query available appointment slots (procedure-first + date range)
  - `book_appointment` — Create a new appointment (with conflict detection)
  - `cancel_appointment` — Cancel an existing appointment
  - `reschedule_appointment` — Move an appointment to a new time
  - `get_practice_info` — Hours, location, contact info
  - `get_providers` — List of providers and their specialties
  - `get_accepted_insurance` — List of accepted insurance plans
  - `lookup_appointment` — Find existing appointments by patient info
  - `update_notes` — Save contextual notes to the session notepad
- Channel-aware system prompt: voice gets a short-response addendum (ADR-029)
- Dynamic date reference table injected every turn (prevents Claude date math errors)
- Handles language detection and bilingual responses
- Token usage logged per turn (input/output tokens tracked in session metrics)

### 5. Mock MacPractice Data Layer (PostgreSQL)
- Simulates MacPractice's scheduling and practice management system
- **All data persisted in PostgreSQL** via asyncpg (raw SQL, no ORM)
- Local dev: PostgreSQL (`voiceagent` database). Production: Supabase free tier.
- Contains: providers, appointments, practice info, insurance plans, patients, sessions, messages
- Seed script (`app/mock_api/data.py`) populates mock data on setup
- Conflict detection on booking (overlapping slots, provider hours, working days)
- All datetimes stored as UTC (TIMESTAMPTZ), converted to practice-local at boundaries

### 6. Email Notifications (ADR-037)
- SendGrid free tier (100 emails/day) for appointment confirmations
- Sends on booking, cancellation, and rescheduling — to both patient and provider
- Fire-and-forget — failures logged, never block the agent response
- HTML templates with practice branding and bilingual support
- "Demo — Not HIPAA Compliant" disclaimer in all emails

### 7. Session Store (PostgreSQL)
- **DB-backed** via `session_repo` — sessions and messages persist across restarts
- Stores: conversation messages, notepad context (JSONB), channel, language, caller number
- Session created on call start or chat connect
- Session expires after inactivity timeout (30 minutes)
- Supports session resumption (chat widget reconnects with existing session_id)

### 8. Admin Dashboard
- Single-file SPA served by FastAPI (Tailwind CDN + ApexCharts)
- Shows: active/recent conversations, booked appointments, agent performance
- Session detail with accordion sections: Transcript, Metrics, Estimated Cost
- Per-session cost breakdown: Claude API tokens, Twilio minutes, Deepgram STT/TTS
- Read-only for MVP (no editing bookings from dashboard)

## Data Flow: Voice Call

```
1. Patient dials Twilio number
2. Twilio sends webhook to our /twilio/incoming endpoint
3. We respond with TwiML to connect Media Stream WebSocket
4. Twilio opens WebSocket, streams audio chunks (mulaw, 8kHz)
5. We forward audio to Deepgram via their streaming API
6. Deepgram returns real-time transcription
7. On end-of-utterance, we send transcription to Agent Core
8. Agent Core calls Claude API with conversation history + tools
9. Claude may call tools (e.g., check_availability) → we execute and return results
10. Claude returns final text response
11. We send text to ElevenLabs TTS API
12. ElevenLabs returns audio stream
13. We forward audio back through Twilio Media Stream
14. Patient hears the response
15. Loop back to step 5 for next utterance
```

## Data Flow: Chat Widget

```
1. Patient opens website with embedded chat widget
2. Widget opens WebSocket to our /chat/ws endpoint
3. Patient types message, sent via WebSocket
4. Chat Handler passes text to Agent Core
5. Agent Core calls Claude API with conversation history + tools
6. Claude may call tools → we execute and return results
7. Claude returns final text response
8. Response sent back via WebSocket
9. Widget displays response
10. Loop back to step 3
```

## Key Design Principles

- **Single agent logic** — Voice and chat share the same Agent Core; only the I/O layer differs
- **Persistent state** — All data in PostgreSQL (sessions, appointments, practice data); durable across restarts and deploys
- **Latency-conscious** — Every component chosen with voice latency in mind (<2-3s total response time target)
- **Single practice, multi-ready** — Data model supports one practice now, but practice_id is in the schema for future expansion
- **Demo-quality, production-thinking** — Mock data, but clean architecture that could connect to real APIs
