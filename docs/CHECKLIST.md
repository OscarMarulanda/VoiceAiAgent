# Implementation Checklist

Phased checklist for building the AI Voice & Chat Agent. Each phase builds on the previous one.

---

## Phase 0: Project Setup
- [ ] Initialize git repo
- [ ] Set up Python project structure (pyproject.toml or requirements.txt)
- [ ] Create virtual environment
- [ ] Install core dependencies (fastapi, uvicorn, anthropic, pydantic)
- [ ] Create app skeleton (main.py, config.py)
- [ ] Set up environment variable loading (.env file, python-dotenv)
- [ ] Create .gitignore (Python, .env, __pycache__, etc.)
- [ ] Set up PostgreSQL local database (`createdb voiceagent`)
- [ ] Create `app/database.py` (asyncpg connection pool + query helpers)
- [ ] Create `migrations/001_initial.sql` (initial schema)
- [ ] Run initial migration locally
- [ ] Verify FastAPI runs locally with health endpoint (including DB ping)
- [ ] Create all documentation files (this checklist, architecture docs, etc.)

## Phase 1: Mock MacPractice API & Data
- [ ] Define Pydantic models (Appointment, Provider, Practice, Patient, TimeSlot, InsurancePlan)
- [ ] Create DB tables for: providers, appointments, practice_info, insurance_plans, patients
- [ ] Write seed script to populate mock data into PostgreSQL (practice info, providers, schedules, insurance list, sample patients)
- [ ] Implement scheduling logic with asyncpg queries (get_available_slots with conflict detection)
- [ ] Implement book_appointment (with conflict check, writes to DB)
- [ ] Implement cancel_appointment (updates DB)
- [ ] Implement reschedule_appointment (with conflict check, updates DB)
- [ ] Implement lookup_appointments (by name or phone, queries DB)
- [ ] Implement practice info queries (get_practice_info, get_providers, get_accepted_insurance — all from DB)
- [ ] Write unit tests for scheduling logic (especially conflict detection)
- [ ] Populate pre-existing appointments via seed script (relative to current date)

## Phase 2: Agent Core (Claude API + Tool Calling)
- [x] Add `context JSONB` column to sessions table (migration 002)
- [x] Update Session model and session_repo for notepad context
- [x] Write system prompt (personality, small talk + redirect, capabilities, constraints, bilingual)
- [x] Define Claude API tool schemas (9 tools: 8 domain + update_notes)
- [x] Implement tool execution dispatcher
- [x] Enhance check_availability: procedure-first search + date range (single SQL query)
- [x] Refactor _compute_slots() as pure shared function (no code duplication)
- [x] Implement core agent logic (process_message with notepad + recent window + tool loop, max 6 calls)
- [x] Implement hybrid notepad updates (programmatic from tools + update_notes for soft context)
- [x] Test agent via simple HTTP endpoint (POST /chat/test — temporary, for development)
- [x] Test tool calling works (booking flow verified end-to-end, FAQ verified)
- [x] Test bilingual responses (Spanish input → Spanish output verified)
- [x] Test edge cases (cancellation, rescheduling — fixed bugs found during testing)
  - Bug fix: notepad now stores `found_appointments` from lookup (ADR-021)
  - Bug fix: availability slots include `day` + `display` fields (ADR-020)
  - Bug fix: system prompt includes explicit date mapping table (ADR-020)
  - Bug fix: timezone handling — practice-local at boundaries, UTC in DB (ADR-022, migration 003)
- [x] Test edge cases (double booking, past dates, unknown provider — all passing)
  - Bug fix: `check_availability` now accepts `provider_name` param, resolves to ID internally (ADR-023)
  - Bug fix: system prompt instructs agent to verify unknown providers before collecting patient info
  - Added `provider_repo.find_by_name()` for name-based provider lookup
- [x] Write unit tests for agent (mock Claude API + real Claude integration tests)
  - 16 pure function tests (message building, notepad, text extraction)
  - 8 tool execution tests (real DB, no Claude)
  - 5 mocked Claude tests (tool loop cap, API errors, session handling, notepad persistence)
  - 5 integration tests with real Claude API (FAQ, insurance, booking, cancellation, Spanish)
  - Total: 61 tests across all test files (test_agent, test_scheduling, test_practice)

## Phase 3: Chat Widget & WebSocket
- [x] Implement WebSocket endpoint (/chat/ws) — `app/chat/routes.py` (ADR-036)
- [x] Handle WebSocket lifecycle (connect, message, disconnect, errors)
- [x] Integrate with Agent Core (message → agent → response, 30s timeout)
- [x] Implement typing indicator (send "typing" event while processing)
- [x] Build chat widget HTML/CSS (clean, responsive, embedded CSS in Shadow DOM)
- [x] Build chat widget JavaScript (WebSocket, UI, auto-reconnect with exponential backoff)
- [x] Encapsulate widget in Shadow DOM (`all: initial` + `!important` font reset)
- [x] Add configuration via data attributes (server, practice, color, position, greeting)
- [x] Test widget in a standalone HTML page (`test.html`)
- [x] Test widget embedded in a WordPress-like page (`test-wordpress.html` — aggressive CSS conflicts)
- [x] Test mobile responsiveness
- [x] Add session persistence in sessionStorage
- [x] Add application-level ping/pong keepalive (30s interval, 60s timeout)
- [x] Add reset conversation button in header
- [x] Add lightweight markdown rendering for agent messages (bold, lists, line breaks)
- [x] Add auto-focus on input after agent response

## Phase 4: Voice Pipeline (Twilio + Deepgram + ElevenLabs)
- [x] Set up Twilio account, buy phone number (+1 402 243 6878)
- [x] Set up Deepgram account + API key
- [x] Set up ElevenLabs account + API key + voice ID
- [x] Decide audio format: request ulaw_8000 from ElevenLabs directly, no conversion (ADR-024)
- [x] Decide streaming strategy: stream TTS chunks directly to Twilio (ADR-025)
- [x] Decide interruption handling: stop TTS on patient speech via Twilio clear event (ADR-026)
- [x] Decide greeting strategy: pre-generate and cache at startup (ADR-027)
- [x] Implement /twilio/incoming webhook (returns TwiML for Media Stream)
- [x] Implement /twilio/media-stream WebSocket handler
- [x] Implement CallSession pattern (ADR-028) — one object per call owns lifecycle + state
- [x] Integrate Deepgram streaming STT
  - [x] Open Deepgram WebSocket on stream start
  - [x] Forward Twilio audio to Deepgram
  - [x] Handle transcription results (interim + final)
  - [x] Handle endpointing (end of utterance detection via speech_final + UtteranceEnd backup)
- [x] Integrate ElevenLabs streaming TTS
  - [x] Send agent response text to ElevenLabs
  - [x] Receive streaming audio chunks (ulaw_8000 format — ADR-024)
  - [x] Forward chunks directly to Twilio (no conversion — ADR-024)
- [x] Wire it all together: audio in → STT → Agent → TTS → audio out
- [x] Pre-generate greeting audio at startup (ADR-027)
- [x] Implement interruption handling (stop TTS via Twilio clear event — ADR-026)
- [x] Test with a real phone call (manual E2E test) — FIRST CALL SUCCESSFUL
  - Greeting plays correctly (ElevenLabs TTS, ulaw_8000)
  - Deepgram STT transcribes speech correctly
  - Agent processes and responds via TTS
  - Appointment booked successfully and saved to DB (Oscar Marulanda, cleaning, Mon Mar 16 9:30 AM)
  - Bugs found during testing (see below)
- [x] Fix voice-specific bugs from first test call:
  - [x] Agent too wordy for voice — voice-specific system prompt addendum (ADR-029)
  - [x] Agent talked over patient during phone number dictation — smart transcript accumulation (ADR-030)
  - [x] Race condition causing false re-processing — asyncio.Lock on processing (ADR-034)
  - [x] Add proper logging — logging.basicConfig in main.py (timestamps, module names)
- [x] Additional improvements from test calls:
  - [x] Filler phrases while agent is thinking — pre-cached at startup, play after 1.5s delay (ADR-031)
  - [x] Farewell detection — regex bypass skips agent for "no thank you", "bye", etc. (ADR-032)
  - [x] Past slot filtering — check_availability no longer returns past times for today (ADR-033)
  - [x] Agent timeout — 15s timeout on process_message to prevent silent hangs
- [x] Implement silence detection (patient goes quiet — ADR-009, ADR-035)
  - 20s silence → "Are you still there?" warning
  - 30s silence → "It seems we got disconnected. Goodbye!" + end call (4s audio drain delay)
  - Timer starts after agent finishes speaking, resets on any transcript
- [x] Measure and log latency at each stage (ADR-035)
  - Logs agent_ms, tts_first_chunk_ms, total_turn_ms per turn
- [x] Implement error handling and fallbacks (ADR-009, ADR-035)
  - Pre-cached error audio clip at startup for TTS/STT failure fallback
  - ElevenLabs failure → plays cached error clip
  - Deepgram connection drop → plays cached error clip + ends call gracefully
  - Unhandled processing errors → plays cached error clip

## Phase 4.5: Email Notifications (SendGrid) — ADR-037
- [ ] Create SendGrid free account + API key
- [ ] Add `SENDGRID_API_KEY` and `NOTIFICATION_FROM_EMAIL` to .env
- [ ] Add `email` column to providers table (migration)
- [ ] Update seed data with provider email addresses
- [ ] Update `book_appointment` tool schema to accept `patient_email`
- [ ] Update system prompt to instruct agent to collect patient email during booking
- [ ] Create `app/notifications/email_service.py` (SendGrid wrapper)
- [ ] Implement booking confirmation email (patient + provider)
- [ ] Implement cancellation notice email (patient + provider)
- [ ] Implement reschedule notice email (patient + provider, old → new time)
- [ ] Add HTML email templates with inline CSS + "Demo — Not HIPAA Compliant" disclaimer
- [ ] Integrate notifications into `tools.py` (fire-and-forget after book/cancel/reschedule)
- [ ] Add bilingual email support (match session language)
- [ ] Test email delivery end-to-end (book via chat/voice → receive email)

## Phase 5: Admin Dashboard (ADR-038)

### 5A: Backend — Migration & API Endpoints
- [x] Create migration 005: add `metrics JSONB` column to sessions table
- [x] Apply migration 005 locally
- [x] Instrument `call_session.py`: persist per-turn metrics to session `metrics` JSONB
- [x] Instrument `chat/routes.py`: persist agent response time to session `metrics` JSONB
- [x] Create admin route group (`app/admin/routes.py` with APIRouter)
- [x] Implement `GET /admin/api/sessions` (list with metrics summary, pagination)
- [x] Implement `GET /admin/api/sessions/{id}` (full transcript + metrics)
- [x] Implement `GET /admin/api/appointments` (date range filter, provider filter, patient search)
- [x] Implement `GET /admin/api/providers` (for calendar columns + filter dropdowns)
- [x] Implement `GET /admin/api/stats` (rich analytics: today, all-time, breakdowns, latency)
- [x] Register admin router in `main.py`
- [x] Test API endpoints with sample data

### 5B: Frontend — Dashboard SPA
- [x] Create `app/admin/dashboard.html` (single-file SPA with Tailwind CDN + ApexCharts)
- [x] Build tab navigation (Sessions, Appointments, Analytics) with collapsible sidebar
- [x] Add "Demo — Not HIPAA Compliant" disclaimer banner
- [x] Build Sessions tab: session list (channel icon, duration, status, language, outcome)
- [x] Build Sessions tab: session detail drill-down (chat-bubble conversation viewer + metrics panel)
- [x] Build Appointments tab: day view (one column per provider, time slots as rows, 8 AM – 6 PM)
- [x] Build Appointments tab: week view (Mon–Fri grid, appointment blocks with overlap handling)
- [x] Build Appointments tab: date navigation (prev/next, today button)
- [x] Build Appointments tab: provider filter checkboxes
- [x] Build Appointments tab: appointment detail popup (click a block → see details)
- [x] Build Appointments tab: color coding by provider
- [x] Build Appointments tab: cancelled appointments shown as faded/strikethrough (toggle to show/hide)
- [x] Build Analytics tab: summary cards (today + all-time counts) via ApexCharts
- [x] Build Analytics tab: language breakdown (donut chart)
- [x] Build Analytics tab: busiest day of week (vertical bar chart)
- [x] Build Analytics tab: top procedures booked (horizontal bar chart)
- [x] Build Analytics tab: average agent latency (radial gauge)
- [x] Test dashboard with real session data (voice call with metrics confirmed working)

## Phase 6: Polish & Integration Testing
- [x] Test full voice flow end-to-end (call → book appointment → verify in dashboard)
- [ ] Test full chat flow end-to-end (widget → book appointment → verify in dashboard)
- [x] Test bilingual voice flow (Spanish call)
- [ ] Test bilingual chat flow (Spanish chat)
- [ ] Test error scenarios (slow response, unclear input)
- [ ] Test concurrent sessions (two calls at once, or call + chat)
- [ ] Review and refine system prompt based on test results
- [ ] Add rate limiting
- [ ] Add request logging
- [ ] Performance optimization (latency reduction if needed)
- [x] Fix buffer timer race condition — short transcripts silently cancelled when new transcript arrived mid-processing
- [x] Fix dashboard timezone bug — `calUTCtoLocal` double-converted times when browser timezone != practice timezone
- [x] Add bilingual TTS — separate Deepgram Aura-2 voices per language (EN: aura-2-asteria-en, ES: aura-2-selena-es)
- [x] Add language detection — regex-based detection from first transcript, persisted to session DB
- [x] Add Spanish farewell detection + common Deepgram mistranscription patterns
- [x] Fix farewell interruption — disconnect STT before playing goodbye to prevent VAD cutoff
- [x] Add agent goodbye detection — if agent response contains goodbye language, disconnect STT + end call
- [x] Add token usage tracking — per-turn logging + session-level metrics + dashboard display
- [x] Fix slot confusion — numbered slots with inline ISO timestamps prevent Claude from booking wrong times
- [x] Add sendgrid_api_key to Settings config
- [x] Push to GitHub (https://github.com/OscarMarulanda/VoiceAiAgent)
- [x] Add README.md
- [x] Add per-session cost breakdown in dashboard (Claude API, Twilio, Deepgram STT/TTS)
- [x] Add chat session token tracking (parity with voice sessions)
- [x] Add TTS character tracking for voice sessions
- [x] Make chat widget launcher draggable
- [x] Refactor session detail into accordion (Transcript, Metrics, Estimated Cost)
- [x] Upgrade STT from Deepgram Nova-2 to Nova-3

## Phase 7: MCP Server (Bonus)
- [ ] Install MCP Python SDK
- [ ] Create MCP server that wraps mock API functions
- [ ] Define MCP tools (same as Claude API tools)
- [ ] Test MCP server standalone
- [ ] Document MCP server usage
- [ ] (Optional) Create a demo showing Claude Desktop connecting to MCP server

## Phase 8: Deployment
- [ ] Create Dockerfile or Procfile
- [ ] Configure Railway/Render project
- [ ] Set environment variables in deployment platform
- [ ] Deploy and verify health endpoint
- [ ] Configure Twilio webhook URLs to point to deployed server
- [ ] Test live voice call to deployed server
- [ ] Test live chat widget pointing to deployed server
- [ ] Set up custom domain (optional)
- [ ] Set up billing alerts on all services
- [ ] Create a simple landing page with:
  - [ ] Phone number to call
  - [ ] Embedded chat widget
  - [ ] Brief description of the project
  - [ ] Link to GitHub repo

## Phase 9: Documentation & Presentation
- [ ] Update all docs with final implementation details
- [ ] Write README.md (setup instructions, architecture overview, demo links)
- [ ] Record a demo video (voice call + chat widget + dashboard)
- [ ] Prepare talking points for interview:
  - [ ] Architecture decisions and trade-offs
  - [ ] How this could integrate with real MacPractice APIs
  - [ ] Scaling considerations
  - [ ] HIPAA compliance path
  - [ ] Multi-practice expansion plan

---

## Current Phase: 6 (Polish & Integration Testing)

**Completed:** Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5
**Next:** Phase 4.5 (Email Notifications) or Phase 6 (Polish & Integration Testing)
