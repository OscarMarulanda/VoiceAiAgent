# Modules

Detailed breakdown of every module in the system, its responsibilities, and interfaces.

---

## Module Map

```
app/
├── main.py                      # FastAPI app entry point, CORS, lifespan
├── config.py                    # Environment variables, settings
├── database.py                  # asyncpg connection pool and query helpers
│
├── domain/                      # Pure business logic — NO database imports
│   ├── models/                  # Pydantic models (entities)
│   │   ├── appointment.py       # Appointment, AppointmentType, TimeSlot
│   │   ├── provider.py          # Provider
│   │   ├── practice.py          # Practice
│   │   ├── patient.py           # Patient
│   │   ├── insurance.py         # InsurancePlan
│   │   └── session.py           # Session, Message
│   └── services/                # Business rules (call repositories, never DB directly)
│       ├── scheduling.py        # Availability, booking, conflict detection, cancellation
│       └── practice.py          # Practice info, providers, insurance queries
│
├── repositories/                # Database access — raw SQL via asyncpg
│   ├── appointment_repo.py      # Appointment CRUD queries
│   ├── provider_repo.py         # Provider queries
│   ├── practice_repo.py         # Practice + insurance + appointment type queries
│   ├── patient_repo.py          # Patient queries
│   └── session_repo.py          # Session and message queries
│
├── agent/                       # AI Agent Core
│   ├── core.py                  # Main agent logic, Claude API integration
│   ├── tools.py                 # Tool definitions and execution dispatch
│   └── prompts.py               # System prompts, prompt templates
│
├── voice/                       # Voice pipeline (Call Session pattern — ADR-028)
│   ├── routes.py                # POST /twilio/incoming + WS /twilio/media-stream
│   ├── call_session.py          # CallSession: lifecycle, state, pipeline orchestration
│   ├── stt.py                   # DeepgramSTT: stateless streaming STT wrapper
│   └── tts.py                   # ElevenLabsTTS: stateless streaming TTS + greeting cache
│
├── chat/                        # Chat widget WebSocket endpoint
│   └── routes.py                # WS /chat/ws (session mgmt, typing, ping/pong)
│
├── admin/                       # Admin dashboard (Phase 5 — ADR-038)
│   ├── routes.py                # GET /admin/*, API endpoints
│   └── dashboard.html           # Single-file SPA (Phase 5B — not yet built)
│
├── notifications/                # Email notifications (Phase 4.5 — planned, not yet built)
│   └── email_service.py         # SendGrid wrapper: booking/cancel/reschedule emails
│
├── utils/                       # Shared utilities
│   └── timezone.py              # Timezone conversion (local↔UTC, practice tz cache)
│
├── mock_api/                    # Seed script (standalone, not part of architecture)
│   └── data.py                  # Populates DB with mock data (times in Pacific→UTC)
│
└── widget/                      # Chat Widget (Frontend)
    ├── widget.js                # Self-contained widget (JS + embedded CSS in Shadow DOM)
    ├── test.html                # Standalone test page
    └── test-wordpress.html      # WordPress-like test page (aggressive CSS conflicts)

migrations/
├── 001_initial.sql              # Initial database schema
├── 002_session_context.sql      # Session context JSONB column
├── 003_practice_timezone.sql    # Practice timezone column
├── 004_appointment_updated_at.sql # Appointment updated_at + auto-update trigger
└── 005_session_metrics.sql      # Session metrics JSONB column (ADR-038)

tests/
├── conftest.py                  # DB pool fixture
├── test_scheduling.py           # Scheduling service tests
├── test_practice.py             # Practice info tests
└── test_agent.py                # Agent tests (pure functions, tool execution, mocked Claude, integration)
```

**Architecture flow:**
```
API route → Agent Core → Domain Service → Repository → Database
```

---

## Module Details

### 1. `app/main.py` — Application Entry Point

**Responsibility:** Initialize FastAPI app, configure middleware, register routes, manage lifespan events, configure logging.

**Key elements:**
- `logging.basicConfig()` — Configures root logger at module level (before any imports that create loggers). Format: `HH:MM:SS LEVEL [module] message`
- FastAPI app instance with CORS middleware
- Lifespan handler: init DB pool, pre-generate greeting audio (ADR-027), pre-generate filler phrases (ADR-031)
- Route registration: voice, chat, admin, static files
- Health check endpoint
- Temporary `POST /chat/test` endpoint for Phase 2 development

**Interfaces:**
- `GET /health` — Health check
- `POST /chat/test` — Temporary chat test endpoint
- Registers all sub-routers

---

### 2. `app/config.py` — Configuration

**Responsibility:** Load and validate environment variables, provide typed settings.

**Key settings:**
- `ANTHROPIC_API_KEY` — Claude API key
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` — Twilio credentials
- `DEEPGRAM_API_KEY` — Deepgram API key
- `ELEVENLABS_API_KEY` — ElevenLabs API key
- `ELEVENLABS_VOICE_ID` — Selected voice for TTS
- `CLAUDE_MODEL` — Model to use (default: claude-sonnet-4-20250514)
- `SESSION_TIMEOUT_MINUTES` — Session expiry (default: 30)
- `LOG_LEVEL` — Logging level
- `DATABASE_URL` — PostgreSQL connection string (local or Supabase)
- `PRACTICE_ID` — Current practice identifier (for multi-practice readiness)

---

### 3. `app/database.py` — Database

**Responsibility:** Manage the asyncpg connection pool and provide query helper functions.

**Key elements:**
- `init_pool()` — Create asyncpg connection pool on app startup (called in lifespan)
- `close_pool()` — Close pool on shutdown
- `get_pool()` — Return the pool for use in other modules
- `execute(query, *args)` — Run a query (INSERT, UPDATE, DELETE)
- `fetch(query, *args)` — Run a query and return rows
- `fetchrow(query, *args)` — Run a query and return a single row

**Notes:**
- Uses `asyncpg` directly — raw SQL, no ORM
- Connection string comes from `DATABASE_URL` env var
- Local dev: `postgresql://localhost/voiceagent`
- Production: Supabase connection string

---

### 4. `app/models/` — Data Models

**Responsibility:** Pydantic models shared across modules.

**Models:**
- `Appointment` — id, patient_name, patient_phone, provider_id, datetime, duration_minutes, status, practice_id, reason, notes
- `Provider` — id, name, specialty, practice_id, available_days, working_hours
- `Practice` — id, name, address, phone, hours, website
- `Patient` — name, phone, email (minimal, for booking)
- `TimeSlot` — start, end, provider_id, available (boolean)
- `InsurancePlan` — name, type (PPO/HMO/etc)

---

### 5. `app/agent/core.py` — Agent Core

**Responsibility:** The central AI logic. Takes user input (text), manages conversation via notepad context, calls Claude, executes tools, returns response.

**Key functions:**
- `process_message(session_id: str, user_message: str) -> str` — Main entry point. Takes text input, returns text output.
- `_build_messages(notepad: dict, tool_log: list, recent_messages: list, user_message: str) -> list` — Builds Claude API message array from notepad + recent window (NOT full history)
- `_execute_tool(tool_name: str, tool_input: dict) -> str` — Dispatches tool calls to domain services
- `_handle_tool_loop(response, session) -> str` — Handles multi-turn tool calling until Claude returns text (max 6 calls)
- `_update_notepad_from_tool(notepad: dict, tool_name: str, tool_input: dict, tool_result: dict) -> dict` — Programmatic notepad updates from tool results

**Conversation context (per turn):**
1. Structured notepad (JSONB) — patient_name, phone, found_appointments (from lookup), last_booking, last_availability, context_notes
2. Compact tool call log — what actions were taken and results
3. Last 8 exchanges (16 messages) — recent conversation verbatim

**Interfaces with:**
- `agent/tools.py` for tool definitions
- `agent/prompts.py` for system prompt
- `repositories/session_repo.py` for session + message persistence
- `domain/services/*` for tool execution

---

### 6. `app/agent/tools.py` — Tool Definitions

**Responsibility:** Define Claude API tools and map tool calls to domain service functions.

**Tools defined (9 total):**
```python
TOOLS = [
    {
        "name": "check_availability",
        "description": "Check available appointment slots over a date range. Search by procedure type or provider.",
        "input_schema": {
            # date_from: required — start of search range (YYYY-MM-DD)
            # date_to: optional — end of search range (defaults to date_from + 3 days)
            # appointment_type: optional — procedure name (e.g., "Cleaning", "Root Canal")
            # provider_id: optional — specific provider
            # At least one of appointment_type or provider_id is required
        }
    },
    {
        "name": "book_appointment",
        "description": "Book an appointment for a patient",
        "input_schema": { ... }
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment",
        "input_schema": { ... }
    },
    {
        "name": "reschedule_appointment",
        "description": "Reschedule an existing appointment to a new time",
        "input_schema": { ... }
    },
    {
        "name": "get_practice_info",
        "description": "Get practice information (hours, address, phone, etc.)",
        "input_schema": { ... }
    },
    {
        "name": "get_providers",
        "description": "List providers at the practice with their specialties",
        "input_schema": { ... }
    },
    {
        "name": "get_accepted_insurance",
        "description": "List insurance plans accepted by the practice",
        "input_schema": { ... }
    },
    {
        "name": "lookup_appointment",
        "description": "Look up existing appointments by patient name or phone number",
        "input_schema": { ... }
    },
    {
        "name": "update_notes",
        "description": "Save a contextual note about the patient or conversation for later reference",
        "input_schema": {
            # note: required — free-text note (e.g., "patient is nervous about dental visits")
        }
    }
]
```

**Availability slot output fields:**
- `start` — ISO 8601 timestamp (used for booking)
- `end` — ISO 8601 timestamp
- `day` — Day-of-week name (e.g., "Friday") — computed server-side, not by Claude
- `display` — Human-readable string (e.g., "Friday, March 20 at 02:00 PM") — Claude uses this when presenting options to patients

**Key function:**
- `execute_tool(tool_name: str, tool_input: dict) -> dict` — Routes tool call to correct domain service function, returns result dict + compact summary for tool log.

---

### 7. `app/agent/prompts.py` — System Prompts

**Responsibility:** System prompt that defines agent behavior, personality, and constraints. Channel-aware — appends voice-specific instructions for phone calls (ADR-029).

**Key aspects of the system prompt:**
- Role: Friendly, professional healthcare receptionist AI
- Capabilities: What the agent can and cannot do
- Tone: Warm, patient, clear — appropriate for healthcare
- Language: Detect and respond in caller's language (English/Spanish)
- Safety: Never give medical advice, always suggest contacting provider for clinical questions
- Tool usage: When and how to use each tool
- Dates & Times: Use `display` field from tool results; never self-calculate day-of-week
- Error handling: How to handle failures gracefully
- Information gathering: Collect necessary info before booking (name, phone, reason)

**Voice addendum (ADR-029):**
- `VOICE_ADDENDUM` — Appended when `channel == "voice"`. Forces 1-2 sentence responses, no formatting, conversational tone, patience with partial input.
- `build_system_prompt(..., channel="chat")` — Accepts channel parameter, adds addendum for voice.

**Date reference table:**
- `_build_date_prefix()` dynamically generates an explicit day→date mapping for 2 weeks
- Format: `this Monday = Mar 16 (2026-03-16), next Monday = Mar 23 (2026-03-23)`
- Injected at the top of the system prompt on every API call
- Prevents Claude from doing unreliable date arithmetic (see ADR-020)

---

### 8. `app/voice/routes.py` — Voice Routes (ADR-028)

**Responsibility:** Thin FastAPI route handlers for Twilio. Creates CallSession and delegates.

**Endpoints:**
- `POST /twilio/incoming` — Webhook for incoming calls. Returns TwiML with `<Connect><Stream>` to start Media Stream.
- `WS /twilio/media-stream` — WebSocket for Twilio Media Streams. Creates a `CallSession` and delegates all event handling.

**Key principle:** No business logic in routes — just create session, delegate, clean up.

---

### 9. `app/voice/call_session.py` — Call Session (ADR-028)

**Responsibility:** Owns the full lifecycle of one phone call. Manages state, orchestrates the STT → Agent → TTS pipeline, handles interruptions, smart transcript accumulation, filler phrases, and farewell detection.

**State per call:**
- `stream_sid` — Twilio's stream identifier
- `session_id` — Agent session ID (for conversation history)
- `is_speaking` — Boolean flag, True while sending TTS audio to Twilio
- `_tts_cancelled` — Flag to break TTS streaming loop on interruption
- `twilio_ws` — Reference to Twilio WebSocket connection
- `_stt` — Active Deepgram STT connection
- `_utterance_buffer` — Accumulates short transcripts (ADR-030)
- `_buffer_timer` — asyncio.Task for buffer flush timeout (ADR-030)
- `_processing_lock` — asyncio.Lock preventing concurrent agent calls (ADR-034)
- `_silence_task` — asyncio.Task for silence detection timer (ADR-035)
- `_silence_warning_sent` — Boolean, True after "are you still there?" has been sent
- `_ended` — Boolean flag preventing actions after call termination
- `_tts_first_chunk_t`, `_turn_start_t`, `_agent_ms` — Latency tracking (ADR-035)

**Key methods:**
- `start(caller_number)` — Initialize: create agent session, open Deepgram connection, play cached greeting
- `handle_audio(payload)` — Forward Twilio audio to Deepgram
- `stop()` — Clean up: cancel timers, close STT, end agent session

**Smart accumulation (ADR-030):**
- `_on_transcript(text)` — Buffers short transcripts (<4 words) with 1.5s timer. Flushes immediately for substantial input (4+ words).
- `_buffer_timeout()` — asyncio task that flushes buffer after 1.5s of silence
- `_flush_buffer()` — Joins buffered text, checks farewell regex, sends to agent under processing lock

**Farewell detection (ADR-032):**
- `_FAREWELL_RE` — Strict regex matching common farewells ("no thank you", "bye", "that's all", etc.)
- If matched, plays canned farewell TTS immediately, skips agent entirely

**Agent processing + filler (ADR-031):**
- `_process_and_speak(text)` — Launches fire-and-forget filler task, calls `process_message()` with 15s timeout, cancels filler on completion, streams TTS response
- `_play_filler_after_delay()` — Sleeps 1.5s then plays a random pre-cached filler phrase. Cancelled if agent responds first.
- `_speak(text)` — Streams TTS audio to Twilio, respects `_tts_cancelled` flag

**Interruption handling (ADR-026):**
- `_on_speech_started()` — VAD callback, triggers interruption if `is_speaking`
- `_handle_interruption()` — Sets `_tts_cancelled`, sends Twilio `clear` event

**Silence detection (ADR-035):**
- `_start_silence_timer()` — Starts silence monitor after agent finishes speaking
- `_reset_silence_timer()` — Resets on any transcript received
- `_silence_monitor()` — asyncio task: 20s → warning prompt, 30s → goodbye + end call

**Error handling (ADR-035):**
- `_on_stt_connection_lost()` — Deepgram drop: plays cached error clip, ends call
- `_speak()` catches TTS errors and plays cached error clip as fallback
- `_flush_buffer()` catches processing errors and plays cached error clip
- `_end_call()` — Waits 4s for Twilio to finish playing audio, then closes WebSocket

**Latency logging (ADR-035):**
- Logs `agent_ms`, `tts_first_chunk_ms`, `total_turn_ms` per turn at INFO level
- Measured via `time.monotonic()` in `_process_and_speak()` and `_send_audio_to_twilio()`

**Concurrency:** Each active call holds one CallSession (~few KB + ~45KB filler cache is shared). Processing lock ensures one agent call at a time per session. Different calls process independently.

---

### 10. `app/voice/stt.py` — Deepgram STT Wrapper

**Responsibility:** Wrapper around Deepgram's streaming STT SDK. One instance per active call. Accumulates `is_final` segments and fires transcript callback on `speech_final`.

**Class: `DeepgramSTT`**
- `__init__(on_transcript, on_speech_started, on_connection_lost)` — Callbacks for transcripts, VAD, and connection drops (ADR-035)
- `connect()` — Opens streaming WebSocket to Deepgram, starts background listen task
- `send_audio(audio_bytes)` — Forwards raw mulaw audio to Deepgram
- `close()` — Sets `_closed` flag and closes connection gracefully
- `_on_listen_done(task)` — Done callback on listen task; fires `on_connection_lost` if connection dropped unexpectedly (ADR-035)

**Configuration:**
- Model: Nova-2
- Language: Multi (English + Spanish)
- Encoding: mulaw, sample rate 8000 (matches Twilio's format — no conversion needed)
- Endpointing: 300ms (detects end of speech)
- Utterance end: 1000ms backup (fires if `speech_final` doesn't)
- VAD events: Enabled (for interruption detection)

---

### 11. `app/voice/tts.py` — Deepgram Aura TTS Wrapper + Audio Caches (ADR-024, ADR-027, ADR-031, ADR-035, ADR-039)

**Responsibility:** Stateless wrapper around Deepgram Aura streaming TTS. Manages pre-generated audio caches for greeting and filler phrases. Originally used ElevenLabs; swapped to Deepgram Aura in ADR-039 when the ElevenLabs free tier was exhausted.

**Key functions:**
- `synthesize_stream(text: str) -> AsyncGenerator[bytes]` — Streams raw mulaw/8000 audio chunks from Deepgram
- `generate_greeting() -> bytes` — Generate and cache greeting audio at startup (ADR-027)
- `get_cached_greeting() -> bytes | None` — Return the cached greeting audio
- `generate_fillers() -> None` — Generate and cache 4 filler phrases at startup (ADR-031)
- `get_random_filler() -> bytes | None` — Return a random cached filler phrase
- `generate_error_clip() -> bytes` — Generate and cache error message audio at startup (ADR-035)
- `get_cached_error_clip() -> bytes | None` — Return the cached error audio

**Configuration:**
- Provider: Deepgram Aura (via `httpx` to `/v1/speak` endpoint)
- Voice model: `aura-asteria-en` — handles English and Spanish text
- Output format: `mulaw`, sample rate `8000`, `container=none` (raw bytes, no WAV header)
- Streaming: HTTP chunked response — chunks forwarded directly to Twilio (ADR-025)
- Auth: Uses `DEEPGRAM_API_KEY` (same key as STT)

**Greeting cache (ADR-027):**
- Generated once at app startup via Deepgram API
- Stored as bytes in memory (~33KB)
- Played instantly on call connect (~0ms latency vs 500-800ms for live generation)

**Filler cache (ADR-031):**
- 4 phrases generated sequentially at startup (~48KB audio total)
- Stored as list of bytes in memory
- Played randomly when agent takes >1.5s to respond

**Error clip cache (ADR-035):**
- Single error message generated at startup (~45KB)
- Stored as bytes in memory
- Played on TTS failure, STT connection drop, or unhandled processing errors

---

### 12. `app/chat/routes.py` — Chat WebSocket (ADR-036)

**Responsibility:** WebSocket endpoint for the chat widget. Mirrors the thin-routes pattern from `app/voice/routes.py`.

**Endpoints:**
- `WS /chat/ws` — WebSocket connection for chat

**Key logic:**
- On connect: accept connection, start ping watchdog task
- On first message: create new session or resume existing (validates `session_id` from client)
- On message: send typing indicator, call `process_message()` (30s timeout), send response
- On disconnect: cancel ping watchdog, end session in DB
- Ping/pong: client sends `{"type": "ping"}` every 30s, server responds `{"type": "pong"}`. Connection closed after 60s with no ping.

**Error handling:**
- Agent timeout (30s) → friendly retry message
- Agent exception → friendly error message
- Invalid JSON → error message back to client
- WebSocket disconnect → clean session teardown

---

### 13. `app/mock_api/data.py` — Mock Data

**Responsibility:** Define all mock data for the demo practice.

**Data includes:**
- Practice info (name, address, hours, phone, etc.)
- Providers (3-4 providers with different specialties)
- Weekly schedule templates per provider
- Pre-populated appointments (some slots filled)
- Accepted insurance plans (10-15 plans)
- Sample patients

---

### 14. `app/domain/services/scheduling.py` — Scheduling Logic

**Responsibility:** Appointment CRUD operations with conflict detection and availability search.

**Key functions:**
- `get_available_slots(provider_id, date, duration) -> list[TimeSlot]` — Available slots for one provider, one day
- `get_available_slots_by_type(appointment_type, date_from, date_to) -> list[dict]` — Slots across all providers for a procedure, over a date range. **Single DB query** — JOINs appointment_types → providers → appointments, then computes slots in Python.
- `book_appointment(appointment: Appointment) -> dict` — Books with conflict check
- `cancel_appointment(appointment_id: str) -> dict` — Cancels an appointment
- `reschedule_appointment(appointment_id: str, new_starts_at: datetime) -> dict` — Moves with conflict check
- `lookup_appointments(patient_name, patient_phone) -> list[dict]` — Find existing appointments

**Internal (shared functions, no DB):**
- `_compute_slots(provider_id, date_from, date_to, ...) -> list[TimeSlot]` — Core slot generation shared by both availability functions. Iterates over each day in range, checks working hours and conflicts in memory.
- `_compute_slots_for_day(...)` — Single-day slot computation. Filters out past slots for today (ADR-033) by comparing against `datetime.now(tz)` in the practice's local timezone.
- `_parse_booked_ranges(existing_appointments)` — Convert appointment dicts to (start, end) tuples

**Conflict detection logic:**
- Check if requested time overlaps with any existing appointment for that provider
- Check if time is within provider's working hours
- Check if date is on a day the provider works

---

### 15. `app/mock_api/practice_info.py` — Practice Info Queries

**Responsibility:** Return practice information for FAQ handling.

**Key functions:**
- `get_practice_info() -> Practice` — Full practice details
- `get_providers() -> list[Provider]` — All providers
- `get_accepted_insurance() -> list[InsurancePlan]` — Insurance list
- `get_hours() -> dict` — Formatted hours of operation

---

### 16. `app/mock_api/mcp_server.py` — MCP Server (Bonus)

**Responsibility:** Expose mock API as an MCP server, demonstrating MCP protocol knowledge.

**Details:**
- Uses the MCP Python SDK
- Wraps the same functions from scheduling.py and practice_info.py
- Can be run as a standalone process
- Demonstrates extensibility — other AI tools could connect to this MCP server

---

### 17. `app/repositories/session_repo.py` — Session Repository

**Responsibility:** Store and retrieve conversation sessions, messages, and notepad context via DB.

**Key functions (already implemented):**
- `create_session(channel, practice_id, language, caller_number) -> {id, started_at}` — Insert new session
- `get_session(session_id) -> dict | None` — Query session by ID
- `end_session(session_id)` — Mark session as ended
- `update_language(session_id, language)` — Update detected language
- `add_message(session_id, role, content)` — Append message to history
- `get_messages(session_id) -> list[dict]` — Get all messages for a session
- `list_sessions(active_only, limit, offset) -> list[dict]` — List sessions for admin
- `cleanup_expired(timeout_minutes) -> int` — Delete sessions past TTL

**New for Phase 2:**
- `get_context(session_id) -> dict` — Get the JSONB notepad context
- `update_context(session_id, context: dict)` — Update the JSONB notepad context
- `get_recent_messages(session_id, limit) -> list[dict]` — Get last N messages (for recent window)

**Storage:** PostgreSQL via `asyncpg`. Sessions and context persist across restarts.

---

### 18. `app/notifications/email_service.py` — Email Notifications (Phase 4.5 — planned, not yet built)

**Responsibility:** Send appointment confirmation/cancellation/reschedule emails to patients and providers via SendGrid.

**Planned functions:**
- `send_booking_confirmation(patient_email, provider_email, appointment_details)` — HTML email with booking details
- `send_cancellation_notice(patient_email, provider_email, appointment_details)` — Cancellation confirmation
- `send_reschedule_notice(patient_email, provider_email, old_time, new_time, details)` — Old → new time

**Key design:**
- Fire-and-forget: called from `tools.py` after successful book/cancel/reschedule
- Failures are logged, never block the agent response
- HTML templates with inline CSS, practice branding, bilingual support
- "Demo — Not HIPAA Compliant" disclaimer in footer
- Env vars: `SENDGRID_API_KEY`, `NOTIFICATION_FROM_EMAIL`

---

### 19. `app/admin/` — Admin Dashboard (Phase 5 — ADR-038, planned, not yet built)

**Responsibility:** Web UI for reviewing agent activity, appointment schedule, and analytics.

**Files:**
- `routes.py` — FastAPI router: serves dashboard HTML + JSON API endpoints
- `dashboard.html` — Single-file SPA (embedded CSS + JS, no framework)

**Endpoints:**
- `GET /admin/` — Serves the dashboard HTML page
- `GET /admin/api/sessions` — List sessions with metrics summary (paginated)
- `GET /admin/api/sessions/{id}` — Session detail: full conversation transcript + metrics
- `GET /admin/api/appointments` — Appointments for date range (for calendar rendering)
- `GET /admin/api/providers` — Provider list (for calendar columns + filter dropdowns)
- `GET /admin/api/stats` — Rich analytics (today, all-time, breakdowns, latency)

**Dashboard tabs:**
1. **Sessions** — List view (channel, duration, status, language, outcome) → click for conversation transcript in chat-bubble format + per-session performance metrics
2. **Appointments** — Google Calendar-style view: day view (one column per provider) and week view (7-day grid). Color-coded by provider/procedure. Filter by provider, search by patient name. Date navigation.
3. **Analytics** — Summary cards (today + all-time) + breakdowns: language, channel, busiest day, top procedures, avg agent latency

**Data sources:**
- Sessions + messages from `session_repo` (existing queries + new metrics column)
- Appointments from `appointment_repo.get_all()` (existing, with expanded date range filter)
- Providers from `provider_repo` (existing)
- Stats from aggregate SQL queries (new functions in repos)

**Disclaimer:** "Demo — Not HIPAA Compliant" banner at the top of every page

---

### 20. `app/widget/` — Chat Widget (Frontend) (ADR-036)

**Responsibility:** Embeddable JavaScript chat widget. Single self-contained file with CSS embedded inside Shadow DOM.

**Files:**
- `widget.js` — Full widget: UI, CSS (as template literal), WebSocket, state management
- `test.html` — Standalone test page simulating a dental practice website
- `test-wordpress.html` — Test page with aggressive CSS (`!important` on `*`, Comic Sans, etc.) to verify Shadow DOM isolation

**Features:**
- Single `<script>` tag to embed (zero extra HTTP requests)
- Shadow DOM encapsulation with `all: initial` CSS reset on wrapper element
- Configurable via data attributes: server URL, practice name, primary color, position, greeting
- Floating button → expands to chat window (smooth animation)
- Typing indicator (animated dots) while agent processes
- Auto-reconnect with exponential backoff (1s → 30s, max 10 attempts, manual retry button)
- Application-level ping/pong keepalive (30s interval)
- Session persistence in `sessionStorage` (survives page navigation, cleared on tab close)
- Session resumption on reconnect (sends `session_id` to server)
- Reset button in header to start fresh conversation
- Lightweight markdown rendering for agent messages (bold, lists, line breaks)
- Keyboard support: Enter to send, Escape to minimize
- Responsive: 380px on desktop, full screen on mobile
- Input auto-focuses after each agent response

**Shadow DOM CSS isolation:**
- `all: initial` on `.widget-root` wrapper breaks CSS inheritance from host page
- `font-family` set with `!important` on `*` inside shadow to override inherited fonts
- Verified against aggressive WordPress-like CSS (Comic Sans `!important` on `*`, etc.)

**Embedding example:**
```html
<script src="https://your-server.com/widget/widget.js"
        data-server="https://your-server.com"
        data-practice="Sunshine Dental"
        data-primary-color="#2563eb"
        data-greeting="Hello! How can I help you today?"
></script>
```
