# Architecture Decision Records (ADRs)

Each decision follows the format: Context → Decision → Reasoning → Consequences.

---

## ADR-001: Claude API as the LLM

**Context:** Need an LLM to power the conversational agent. Options include Claude (Anthropic), GPT-4 (OpenAI), open-source models (Llama, Mistral).

**Decision:** Use Claude API (Anthropic) via the `anthropic` Python SDK.

**Reasoning:**
- The role is at MacPractice/Valsoft — demonstrating Claude expertise is strategically valuable
- Claude's tool calling is well-documented and reliable
- Claude handles nuanced healthcare conversations well (empathetic, careful)
- Excellent bilingual (English/Spanish) capabilities
- Claude Sonnet offers good balance of quality and speed for voice latency requirements

**Consequences:**
- Dependency on Anthropic API availability
- Cost per API call (see COSTS.md)
- Model choice (Sonnet vs Haiku) affects both quality and latency

---

## ADR-002: Deepgram for Speech-to-Text

**Context:** Need to convert patient speech from phone calls to text. Options: Twilio built-in `<Gather>`, Deepgram, Google Cloud STT, OpenAI Whisper.

**Decision:** Use Deepgram Nova-2 with streaming/real-time transcription.

**Reasoning:**
- Real-time streaming support — critical for voice latency (we get words as they're spoken)
- High accuracy, especially for medical/dental terminology
- Supports endpointing (detects when the speaker stops) — important for natural turn-taking
- Affordable pricing ($0.0043/min on pay-as-you-go)
- Good Python SDK
- Supports Spanish language recognition (bilingual requirement)

**Trade-offs considered:**
- Twilio `<Gather>`: Simpler but no streaming, limited accuracy, doesn't support our WebSocket audio flow
- Google STT: Good but heavier SDK, more complex setup
- Whisper: Batch-only (not real-time), would add unacceptable latency for voice

**Consequences:**
- Additional API dependency and cost
- Need to handle Deepgram WebSocket connection lifecycle
- Need to handle interim vs. final transcription results

---

## ADR-003: ElevenLabs for Text-to-Speech

**Context:** Need to convert AI text responses to natural-sounding speech. Options: Twilio `<Say>` (Amazon Polly), ElevenLabs, OpenAI TTS, Google Cloud TTS, Deepgram TTS.

**Decision:** Use ElevenLabs for TTS.

**Reasoning:**
- Most natural-sounding voices available — critical for patient trust in healthcare context
- Excellent multilingual support (English and Spanish with same voice)
- Streaming support — can start playing audio before full response is generated
- Voice cloning capability (future: practices could use their own "voice brand")
- Good API and Python SDK

**Trade-offs considered:**
- Twilio `<Say>` / Polly: Simpler, cheaper, but sounds robotic
- OpenAI TTS: Good quality but no streaming in current API
- Deepgram TTS: Would simplify stack (one vendor for STT+TTS) but voice quality not as good

**Consequences:**
- Higher cost per character than alternatives (see COSTS.md)
- Need to handle audio format conversion (ElevenLabs output → Twilio mulaw 8kHz)
- Additional API dependency

---

## ADR-004: Programmatic Tool Calling (Primary) + MCP Server (Bonus)

**Context:** The AI agent needs to interact with the mock scheduling system. Two patterns: programmatic tool calling via Claude API `tools` parameter, or MCP (Model Context Protocol) server.

**Decision:** Programmatic tool calling as the primary integration. MCP server as an additional bonus module.

**Reasoning:**
- Programmatic tool calling is simpler, faster to implement, and well-documented
- Keeps the critical path (voice call latency) simple
- MCP adds infrastructure complexity (server process, transport layer) not justified for MVP
- However, building an MCP server as a bonus demonstrates knowledge of the protocol
- The MCP server wraps the same mock API, so no duplicate logic

**Consequences:**
- Tool definitions maintained in Python code alongside the agent
- MCP server is an optional add-on, not in the critical path
- Both approaches use the same underlying mock data/logic

---

## ADR-005: DB-Backed Session Store (Revised)

**Context:** Need to maintain conversation state across turns within a call or chat session. Options: in-memory dict, Redis, SQLite, PostgreSQL.

**Decision:** ~~In-memory Python dictionary for MVP.~~ **Revised:** Use PostgreSQL via `session_repo` (already built in Phase 1).

**Reasoning (revised):**
- `session_repo` with full CRUD was already built during Phase 1
- DB persistence supports the admin dashboard (Phase 5) without extra work
- Sessions survive server restarts
- Consistent with the rest of the architecture (everything in Postgres)
- No additional dependencies (no Redis needed)

**Consequences:**
- Slight latency per DB query (negligible — local Postgres or Supabase)
- TTL/cleanup logic still needed (already implemented in `session_repo.cleanup_expired()`)
- Admin dashboard can query sessions directly

---

## ADR-006: Single Practice, Multi-Practice Ready

**Context:** Should we build for one practice or many? MacPractice serves thousands of practices.

**Decision:** Build for a single practice now, but include `practice_id` in data models so multi-practice is a schema change, not an architecture change.

**Reasoning:**
- Single practice keeps MVP simple — one set of mock data, no tenant routing
- Including `practice_id` in models is nearly zero extra effort
- Shows architectural foresight without over-engineering

**Consequences:**
- Mock data represents one practice
- No multi-tenant routing, auth, or data isolation in MVP
- Upgrading to multi-practice requires: tenant routing, per-practice config, data isolation

---

## ADR-007: WebSocket for Both Voice and Chat

**Context:** Need real-time bidirectional communication for both voice (Twilio Media Streams) and chat widget.

**Decision:** Use WebSockets for both interfaces.

**Reasoning:**
- Twilio Media Streams requires WebSocket — no choice there
- Chat widget also benefits from WebSocket: real-time, low latency, bidirectional
- Using WebSocket for both keeps the architecture consistent
- FastAPI has excellent WebSocket support
- Alternative for chat (HTTP polling/SSE) adds latency and complexity

**Consequences:**
- Need WebSocket connection management and error handling
- Need to handle disconnection/reconnection in the chat widget
- Slightly more complex than simple HTTP endpoints for chat

---

## ADR-008: Latency Budget Allocation

**Context:** Voice calls need fast responses to feel natural. Industry standard is <2-3 seconds from end of user speech to start of AI speech.

**Decision:** Target 2-second total latency with the following budget:

| Component | Budget | Notes |
|-----------|--------|-------|
| Deepgram endpointing | ~300ms | Detecting end of speech |
| Network (Deepgram → us) | ~50ms | WebSocket, low latency |
| Claude API (first token) | ~800ms | Using Sonnet for speed |
| Tool execution (if needed) | ~100ms | In-memory mock data, fast |
| ElevenLabs TTS (first audio) | ~500ms | Streaming, starts fast |
| Network (us → Twilio) | ~50ms | WebSocket |
| Buffer | ~200ms | Headroom |
| **Total** | **~2000ms** | |

**Reasoning:**
- 2 seconds is at the edge of comfortable conversation pace
- Streaming at every stage (STT, LLM, TTS) is key — don't wait for complete results
- Claude Sonnet chosen over Opus for speed (Haiku would be faster but lower quality)
- Mock data (in-memory) means tool execution is essentially instant
- If latency exceeds budget, we can: use Haiku for simple queries, cache common responses, pre-generate greeting audio

**Consequences:**
- Must use streaming APIs throughout (Deepgram streaming, Claude streaming, ElevenLabs streaming)
- Model choice constrained by latency (Sonnet, not Opus)
- Need latency monitoring/logging to detect degradation

---

## ADR-009: Conversation Error Handling & Fallback Strategy

**Context:** Things will fail — STT might misunderstand, Claude might be slow, the caller might go silent. Need graceful handling.

**Decision:** Implement a tiered fallback strategy:

| Scenario | Response |
|----------|----------|
| STT returns low confidence | Ask the patient to repeat: "I'm sorry, could you say that again?" |
| Claude API timeout (>5s) | Play a filler: "Let me check on that for you..." then retry once |
| Claude API error | "I'm having trouble right now. Let me transfer you to the front desk." (mock transfer) |
| Caller silent >10s | "Are you still there? I'm here to help if you need anything." |
| Caller silent >30s | "It seems we got disconnected. Goodbye!" (end call) |
| Tool execution fails | Claude handles gracefully — told in system prompt to apologize and offer alternatives |
| Unrecognized intent | Claude guided by system prompt to clarify or offer menu of capabilities |

**Consequences:**
- Need timeout handling at every async boundary
- Need to pre-generate or cache filler audio for instant playback
- System prompt must instruct Claude on fallback behaviors

---

## ADR-010: HIPAA Considerations (Demo Scope)

**Context:** Healthcare data is regulated by HIPAA. Even for a demo, showing awareness matters.

**Decision:** Document HIPAA awareness; do not implement full compliance (out of scope for demo).

**What we do:**
- Use only mock/fake patient data — no real PHI (Protected Health Information)
- Do not persist conversation audio or transcripts beyond the session (in-memory only)
- Document what would be needed for production HIPAA compliance
- Include a disclaimer in the admin dashboard: "Demo system — not HIPAA compliant"

**What production would need:**
- BAA (Business Associate Agreement) with all vendors (Twilio, Deepgram, ElevenLabs, Anthropic)
- Encrypted data at rest and in transit
- Access controls and audit logging
- Data retention policies
- Patient consent for AI interaction
- De-identification of any logged data

**Consequences:**
- No real patient data anywhere in the system
- Clear documentation showing HIPAA awareness (impressive for evaluators)
- No compliance burden for the demo

---

## ADR-011: Testing Strategy

**Context:** Need to test voice flows, chat flows, and agent logic without always making real API calls.

**Decision:** Three-tier testing approach:

1. **Unit tests** — Agent core logic, tool execution, mock data operations. No external APIs. Use pytest.
2. **Integration tests** — Test Claude API tool calling with mock data. Uses real Claude API (costs money, run sparingly).
3. **End-to-end manual testing** — Call the real phone number, use the real chat widget. For final validation.

**For voice-specific testing:**
- Use Twilio test credentials for webhook testing without real calls
- Mock Deepgram/ElevenLabs responses in unit tests
- Record sample audio for repeatable integration tests

**Consequences:**
- Unit tests are fast and free — run on every change
- Integration tests use real APIs — run before deployment
- No automated E2E for voice (too complex for MVP) — manual testing checklist instead

---

## ADR-012: Deployment Target

**Context:** Need a live, accessible deployment. Options: Railway, Render, Fly.io, AWS, GCP.

**Decision:** Deploy on **Railway** (primary choice) or **Render** (fallback).

**Reasoning:**
- Railway: Simple, fast deploys from GitHub, good WebSocket support, affordable
- Render: Similar benefits, slightly more mature free tier
- Both support environment variables, custom domains, and Python
- Fly.io: More powerful but more complex setup
- AWS/GCP: Overkill for a demo

**Consequences:**
- Single server deployment (fine for demo scale)
- Need to configure WebSocket support (both platforms support it)
- Need HTTPS (both provide it automatically)
- Environment variables for all API keys

---

## ADR-013: Database — PostgreSQL + asyncpg (No ORM)

**Context:** Need persistent storage for appointments, conversation logs, and session data. Need to choose: database engine, local vs production DB, and whether to use an ORM.

**Decision:**
- **Local dev:** PostgreSQL (already installed locally)
- **Production:** Supabase free tier (existing account, ~24 MB of 500 MB used)
- **Driver:** `asyncpg` — async PostgreSQL driver, raw SQL
- **No ORM** — no SQLAlchemy, no Alembic
- **Migrations:** Manual SQL scripts
- **Keep-alive:** Cron job or scheduled ping to prevent Supabase free tier from pausing after 7 days of inactivity

**Reasoning:**
- PostgreSQL locally matches production (Supabase is Postgres) — no environment mismatch
- Supabase free tier has plenty of space (~476 MB remaining) and costs $0
- `asyncpg` is the fastest Python async Postgres driver — fits our latency-conscious architecture
- No ORM keeps the stack simple, fewer dependencies, less abstraction. Our data model is straightforward enough that raw SQL is manageable
- Manual SQL migration scripts are sufficient for a project this size

**Trade-offs considered:**
- SQLAlchemy ORM: Cleaner Python code, automatic migrations via Alembic, but adds complexity and dependencies we don't need
- SQLite for local dev: Zero setup, but creates an environment mismatch with production Postgres
- Railway Postgres: Always-on but costs ~$1-3/mo from the hosting budget. Supabase is free.

**Consequences:**
- All DB queries are raw SQL strings in Python — must be careful with SQL injection (use parameterized queries always)
- No automatic migration tooling — schema changes tracked as numbered `.sql` files
- Supabase free tier pauses after 7 days idle — must implement a keep-alive mechanism
- Connection string differs between local (`postgresql://localhost/voiceagent`) and production (Supabase connection string) — handled via environment variable

---

## ADR-014: Clean Architecture (Layered)

**Context:** Need to decide how to organize application code. Options: flat structure (everything in one layer), MVC, clean/layered architecture.

**Decision:** Clean architecture with four layers: Domain, Repositories, API, Infrastructure.

**Layers:**
- `domain/models/` — Pydantic entities (no dependencies on anything else)
- `domain/services/` — Business logic (depends on repositories, never on database directly)
- `repositories/` — Raw SQL via asyncpg (depends on database.py and domain models)
- `api/` — FastAPI routes (depends on services)
- `infrastructure/` — External services: Claude, Deepgram, ElevenLabs, Twilio

**Flow:** `API route → Agent Core → Domain Service → Repository → Database`

**Reasoning:**
- Separation of concerns — business logic is testable without mocking the DB layer
- If the mock API is ever replaced with real MacPractice APIs, only the repository layer changes
- Shows production-quality architectural thinking (valuable for the portfolio)
- Repositories contain all raw SQL — easy to audit for injection, easy to optimize queries
- Domain services are pure business logic — easy to reason about and test

**Consequences:**
- More files and directories than a flat structure
- Need discipline to maintain layer boundaries (services never import from database.py)
- Slightly more indirection for simple operations

---

## ADR-015: UTC Storage + Practice-Local Timezone Conversion

**Context:** PostgreSQL `TIMESTAMPTZ` columns store timestamps in UTC. Patient-facing times must be in the practice's local timezone (e.g., "2 PM" means 2 PM Pacific in San Diego). Originally all times were treated as UTC, which caused stored times to be wrong (2 PM stored as 2 PM UTC instead of 2 PM Pacific = 9 PM UTC).

**Decision:** Store all timestamps as UTC in the database. Convert at application boundaries:
- **Inbound** (patient says "2 PM"): interpret as practice-local, convert to UTC before storing
- **Outbound** (displaying to patient): convert UTC to practice-local
- **Internal** (services, DB queries): always UTC

**Implementation:** See ADR-022 for full timezone handling details.

**Reasoning:**
- MacPractice serves practices that may be in different time zones (future multi-practice support)
- `TIMESTAMPTZ` is PostgreSQL best practice — stores in UTC, converts on display
- Boundary conversion ensures anyone reading the DB sees correct UTC values
- Practice timezone stored in `practices.timezone` column

**Consequences:**
- `app/utils/timezone.py` provides conversion utilities
- `tools.py` handles all inbound/outbound conversions (the boundary layer)
- `scheduling.py` converts UTC to local for working-hours validation
- Seed scripts create times in Pacific, convert to UTC for storage
- Tests use Pacific-aware datetimes, convert to UTC for service calls

---

## ADR-016: Conversation History — Notepad + Recent Window (Not Full History)

**Context:** The Claude Messages API is stateless — we must send conversation context on every call. Sending full history grows token usage every turn. For a healthcare receptionist, conversations are task-oriented and structured — we know what information matters.

**Decision:** Use a "notepad" approach inspired by how a real receptionist works: structured notes + a short recent window.

Each API call to Claude includes:
1. **Structured notepad (JSONB)** — Key facts: patient_name, phone, language, reason, insurance, context_notes, found_appointments (from lookup), last_booking, last_availability
2. **Compact tool call log** — What actions were taken and their results (e.g., `{"tool": "check_availability", "result": "3 slots Tue with Dr. Chen"}`)
3. **Last 8 exchanges (16 messages)** — Recent conversation verbatim for conversational flow

**Notepad updates — Hybrid approach:**
- **Programmatic:** Tool results automatically update structured fields (e.g., `book_appointment` result fills patient_name, phone, appointment details)
- **LLM-driven:** An `update_notes` tool allows Claude to save soft context (e.g., "patient is nervous about dental visits", "prefers morning appointments")

**Reasoning:**
- A receptionist doesn't replay the entire conversation — they glance at their notepad
- Our domain is structured: we *know* what matters (name, phone, reason, insurance, actions taken)
- Token usage stays roughly constant regardless of conversation length
- Cheaper than summary buffer (no extra summarization API calls)
- Structured JSON is faster for Claude to parse than free-text summaries
- Recent window preserves conversational flow and tone
- `update_notes` tool captures nuance that programmatic extraction can't

**Trade-offs considered:**
- Full history: Perfect recall but growing token cost — overkill for 5-15 turn conversations
- Sliding window only: Loses early context (patient name said in turn 1)
- Summary buffer hybrid: General-purpose but requires extra LLM summarization calls
- Notepad is a domain-optimized summary buffer — structured where possible, flexible where needed

**Consequences:**
- Need a `context JSONB` column on the `sessions` table (migration 002)
- Session model gains a `context` field
- `session_repo` needs methods to update the context JSONB
- 9 tools instead of 8 (adding `update_notes`)
- Risk: notepad could miss something — mitigated by the 8-exchange recent window

---

## ADR-017: Procedure-First Availability Search with Date Range

**Context:** When patients call for an appointment, they typically know what they need (cleaning, root canal) but not which provider to see. They also give approximate dates — "maybe next Tuesday" — but would accept nearby days. The original `check_availability` required a `provider_id` and a single date.

**Decision:** Make `check_availability` accept:
- `appointment_type` (optional) — searches across all providers who offer that procedure
- `provider_id` (optional) — searches a specific provider (at least one of the two required)
- `date_from` (required) + `date_to` (optional) — date range to search, defaults to 3 days

**Implementation — single SQL query:**
One query JOINs `appointment_types → providers → appointments` to fetch all matching providers and their existing appointments for the full date range. Slot computation iterates over days in Python — no additional DB calls.

```python
# Core function: 1 query, then pure Python
get_available_slots_by_type(appointment_type, date_from, date_to) -> list[dict]
```

Shared slot computation logic is extracted into `_compute_slots()` (pure function, no DB), used by both single-provider and procedure-first searches — zero code duplication.

**Flow:**
1. Patient: "I need a cleaning, maybe next Tuesday"
2. Agent calls `check_availability(appointment_type="Cleaning", date_from="2026-03-17")`
3. Single DB query finds providers who do cleanings + their appointments for Tue-Thu
4. Python computes slots for each day, skipping non-working days
5. Returns: `[{provider: "Dr. Chen", slots: [Tue 10am, Wed 2pm, ...]}, ...]`
6. Agent presents best options across the range

**Reasoning:**
- Matches real patient behavior — they care about the procedure, not the provider
- Date ranges avoid burning tool calls checking one day at a time
- Single DB query instead of N+1 queries — uses existing `idx_appointments_provider_time` index
- Default 3-day range provides flexibility without overwhelming the patient with options
- Agent can widen the range if no slots found ("Let me check later in the week...")

**Consequences:**
- `check_availability` tool schema has `date_from` + optional `date_to` (replaces single `date`)
- `scheduling.get_available_slots_by_type()` handles the single-query approach
- `_compute_slots()` is a pure function shared by single-day and range searches
- Provider-specific search (`provider_id` given) still works as single-day for simplicity
- No new DB indexes needed — existing `idx_appointments_provider_time` covers the query

---

## ADR-018: Agent Tool Loop Cap

**Context:** Claude's tool calling can loop — each tool result may trigger another tool call. Unbounded loops risk runaway API costs and latency.

**Decision:** Cap the tool loop at 6 tool calls per user message.

**Reasoning:**
- A typical turn needs 1-3 tool calls (e.g., check_availability + book_appointment)
- The most complex realistic flow: get_providers → check_availability → book_appointment → update_notes = 4 calls
- 6 provides comfortable headroom without allowing runaway behavior
- If the cap is hit, the agent returns a graceful message asking the user to try again

**Consequences:**
- `process_message()` in `core.py` enforces a counter in the tool loop
- If limit is reached, return a friendly fallback message
- Keeps per-turn costs predictable

---

## ADR-019: Agent Personality and Conversation Style

**Context:** The agent represents a dental practice to patients. Tone and behavior directly affect patient trust and experience.

**Decision:** The system prompt defines a friendly, professional healthcare receptionist that:
- Is warm, patient, and clear — appropriate for healthcare
- Engages in brief small talk when the caller initiates (e.g., "How are you today?" → responds warmly, then redirects)
- Gracefully steers the conversation back to the reason for the call
- Detects language (English/Spanish) and responds in kind
- Never gives medical advice — redirects clinical questions to the provider
- Collects required information before booking (name, phone, reason)
- Confirms details before executing actions (booking, cancelling)
- Handles errors gracefully with apologies and alternatives

**Reasoning:**
- Healthcare patients need to feel heard and respected
- Small talk capability makes the AI feel more human and less robotic
- Redirecting back to business keeps calls efficient
- Confirmation before actions prevents mistakes
- Bilingual support serves a diverse patient population (San Diego setting)

**Consequences:**
- System prompt must be carefully crafted to balance friendliness with efficiency
- Small talk handling increases token usage slightly but improves experience
- Language detection relies on Claude's built-in multilingual ability

---

## ADR-020: Date Handling — Explicit Calendar in System Prompt

**Context:** During Phase 2 edge case testing, Claude consistently miscalculated dates. When a patient asked for "next Saturday" (March 21), Claude would say "Saturday, March 22" — but March 22 is a Sunday. This happened even with a flat date list in the prompt. Claude's date arithmetic is unreliable.

**Decision:** Three-layer defense against date errors:

1. **System prompt: explicit day→date mapping table** — Generated dynamically by `_build_date_prefix()` in `prompts.py`. Lists every day of the week with "this X = Mar DD (YYYY-MM-DD), next X = Mar DD (YYYY-MM-DD)" so Claude can look up dates without doing math. Prompt explicitly says: "never compute your own dates."

2. **Tool output: `day` and `display` fields** — `check_availability` results include `"day": "Friday"` and `"display": "Friday, March 20 at 02:00 PM"` for each slot. Claude uses these when presenting options to the patient, eliminating self-calculated day names.

3. **System prompt instruction** — "Dates & Times" section tells Claude to use the `display` field from tool results and never calculate day-of-week itself.

**What we tried that didn't work:**
- Simple "Today's date is Wednesday, March 11, 2026" — Claude still miscalculated other dates
- Adding just a `day` field to tool output — Claude ignored it
- Flat 14-day date list — Claude still picked wrong dates
- Weekly calendar grouped by "This week" / "Next week" — Claude still got it wrong
- Stronger prompt wording ("IMPORTANT", "never calculate") — not enough

**What worked:** The explicit `this X = date, next X = date` mapping for each day of the week. This requires zero reasoning — just pattern matching on the day name.

**Reasoning:**
- LLMs are notoriously bad at date arithmetic
- A lookup table is cheap (adds ~200 tokens to system prompt) and eliminates the problem
- The `display` field in tool output provides a second safety net for presenting times
- Together these make date errors extremely unlikely

**Consequences:**
- `_build_date_prefix()` generates the table dynamically on each API call (uses `datetime.now()`)
- System prompt is ~200 tokens larger
- Tool output is slightly larger per slot (two extra fields)
- Covers a 2-week window — sufficient for typical appointment booking

---

## ADR-021: Notepad Stores Appointment Details from Lookup

**Context:** During Phase 2 edge case testing, the cancellation flow failed across turns. Turn 1: Claude called `lookup_appointment`, found the appointment (including its ID), and told the patient about it. Turn 2: the patient confirmed cancellation, but Claude couldn't call `cancel_appointment` because the appointment ID was lost — tool call results from turn 1 are not persisted in the message history, and the notepad only stored `patient_name` and `patient_phone`.

**Decision:** `_update_notepad_from_tool` now stores `found_appointments` in the notepad when `lookup_appointment` returns results. Each entry includes `id`, `type`, `provider`, `starts_at`, and `status`.

**Reasoning:**
- Cancel and reschedule flows require the appointment ID, which is only available from the lookup result
- The notepad is injected into every subsequent Claude API call, so the ID persists across turns
- This matches how a real receptionist works — they note down the appointment details after looking them up

**Consequences:**
- `found_appointments` list in notepad enables multi-turn cancel/reschedule flows
- Slightly larger notepad JSON per turn (one entry per found appointment)
- No additional DB queries needed — data comes from the existing lookup result

---

## ADR-022: Practice Timezone Handling

**Context:** The system originally treated all times as UTC. When a patient said "2 PM", it was stored as 2 PM UTC — but the practice is in San Diego (Pacific Time, UTC-7/UTC-8). This meant stored times were 7-8 hours off from their intended local meaning. Anyone querying the DB directly would see wrong times.

**Decision:** Production-style timezone handling with boundary conversions:

1. **Database:** Stays UTC (`TIMESTAMPTZ`). No schema change to time columns.
2. **Practice timezone:** New `timezone` column on `practices` table (IANA format, e.g., `America/Los_Angeles`). Migration 003.
3. **Conversion utility:** `app/utils/timezone.py` provides `local_to_utc()`, `utc_to_local()`, and `get_practice_tz()` (cached).
4. **Inbound (tools.py):** When Claude passes a time from a patient (e.g., `"2026-03-16T14:00:00"`), interpret as practice-local and convert to UTC before passing to services.
5. **Outbound (tools.py):** When returning times to Claude (availability slots, lookup results), convert from UTC to practice-local for display.
6. **Working hours validation:** `_is_within_working_hours()` in scheduling.py converts UTC `starts_at` to local before comparing with working-hours definitions (which are in local time).
7. **Slot computation:** Receives local-aware dates, generates slots in local time. DB queries use UTC boundaries.
8. **System prompt:** `_build_date_prefix()` uses `datetime.now(practice_tz)` so "today" is correct in the practice's timezone.
9. **Seed data:** Creates appointment times in Pacific, converts to UTC before DB insert.

**Boundary diagram:**
```
Patient says "2 PM"
  → Claude sends "2026-03-16T14:00:00" (naive, no tz)
  → tools.py: local_to_utc() → "2026-03-16T21:00:00+00:00" (UTC)
  → DB stores: 2026-03-16 21:00:00+00
  → tools.py: utc_to_local() → "2026-03-16T14:00:00-07:00" (Pacific)
  → Claude tells patient: "2:00 PM"
```

**Reasoning:**
- This is how production systems (Google Calendar, Calendly) handle timezones
- DB is always UTC — universally correct, no ambiguity
- Conversion at the edges keeps services timezone-agnostic
- Practice timezone in DB supports future multi-practice with different timezones
- Uses Python stdlib `zoneinfo` — no extra dependencies, handles DST automatically

**Consequences:**
- `tools.py` is the primary boundary layer for timezone conversion
- `get_practice_tz()` is cached (single DB lookup per practice)
- Working hours are always interpreted as local time (intuitive for practice staff)
- Tests use Pacific-aware datetimes, convert to UTC for service calls
- Re-seed required after migration (existing UTC-stored times are wrong)

---

## ADR-023: Provider Name Resolution in Tools

**Context:** During Phase 2 edge case testing, Claude consistently fabricated provider IDs when patients asked for a provider by name. For example, a patient asking for "Lisa Park" would cause Claude to call `check_availability(provider_id="lisa_park")` — but the real ID is `prov_004`. The tool returned "no availability" because the provider didn't exist, giving the patient a false negative.

**Decision:** Add a `provider_name` parameter to `check_availability` that resolves to a `provider_id` internally via `provider_repo.find_by_name()` (case-insensitive partial match). Also add a system prompt instruction to verify unknown providers before collecting patient info.

**Changes:**
1. `check_availability` tool schema: new `provider_name` string parameter, preferred over `provider_id`
2. `_handle_check_availability()` in tools.py: resolves `provider_name` → `provider_id` before proceeding. Returns a clear error if no match, suggesting `get_providers`.
3. `provider_repo.find_by_name()`: case-insensitive partial match (`ILIKE`), returns best match.
4. System prompt (Booking Flow section): "If a patient asks for a provider by name, call check_availability (with provider_name) or get_providers right away — before collecting the rest of their info."

**Reasoning:**
- Claude naturally uses names, not opaque IDs — the tool interface should match Claude's behavior
- Name resolution in the tool layer is more reliable than hoping Claude calls `get_providers` first
- The prompt instruction ensures unknown providers are caught immediately (better UX than collecting all info then failing)
- `provider_id` is kept as a fallback for cases where Claude already has the ID from a prior tool result

**Consequences:**
- Claude can pass `provider_name="Lisa Park"` directly — no need to know `prov_004`
- Unknown providers get a clear error with guidance to list available providers
- One extra DB query per name resolution (negligible cost)
- `provider_id` still works for backward compatibility with existing tool flows

---

## ADR-024: Audio Format — Request ulaw_8000 from ElevenLabs

**Context:** Twilio Media Streams requires mulaw 8kHz audio. ElevenLabs can output multiple formats including mp3, pcm, and ulaw. We need to decide whether to request a compatible format directly or convert on our side.

**Decision:** Request `ulaw_8000` output format directly from the ElevenLabs API. No server-side audio conversion.

**Reasoning:**
- ElevenLabs supports `ulaw_8000` as a native output format parameter
- Eliminates the need for any audio conversion library (audioop-lte, ffmpeg, pydub)
- Fewer dependencies = simpler deployment and fewer failure points
- Audio goes straight from ElevenLabs → base64 encode → Twilio with zero processing

**Fallback:** If `ulaw_8000` quality is poor, switch to requesting `pcm_22050` and convert to mulaw 8kHz using `audioop-lte` (pure Python, lightweight).

**Consequences:**
- No audio conversion code or dependencies needed (unless fallback is triggered)
- Slightly less flexibility in audio quality tuning vs. converting from higher-quality PCM
- Format is locked to what ElevenLabs supports — but ulaw_8000 is a standard telephony format

---

## ADR-025: Streaming Strategy — Stream TTS Chunks Directly to Twilio

**Context:** After ElevenLabs generates TTS audio, we need to get it to the caller via Twilio. Options: stream chunks as they arrive (lowest latency), buffer by sentence (medium latency), or buffer full response (highest latency).

**Decision:** Stream each TTS audio chunk to Twilio as it arrives from ElevenLabs.

**Reasoning:**
- Lowest latency approach (~500ms to first audio vs 2-4s for full buffering)
- ElevenLabs streaming API sends audio in chunks — we simply base64-encode each chunk and forward to Twilio via the Media Stream WebSocket
- Simpler than sentence-level streaming (no sentence boundary detection, no multiple TTS requests)
- Stays within our 2-second latency budget (ADR-008)

**Future optimization:** Sentence-level streaming (buffer Claude's streamed tokens until sentence boundary, send each sentence to TTS independently) could further reduce perceived latency for multi-sentence responses. Deferred to Phase 6 if needed.

**Consequences:**
- First audio reaches the caller as fast as possible
- No buffering logic needed — straightforward async chunk forwarding
- Audio may have micro-gaps between chunks if network is slow (unlikely with modern infra)

---

## ADR-026: Interruption Handling — Stop TTS on Patient Speech

**Context:** When the AI is speaking (TTS audio streaming to Twilio) and the patient starts talking, we need to decide: keep playing (awkward), or stop and listen (natural).

**Decision:** Stop TTS playback immediately when Deepgram detects patient speech. Use Twilio's `clear` event to flush queued audio.

**Implementation:**
1. Track `is_speaking` state in the call session (True while sending TTS audio to Twilio)
2. When Deepgram sends a transcript while `is_speaking` is True:
   - Send `{"event": "clear", "streamSid": "..."}` to Twilio (flushes audio queue)
   - Stop forwarding any remaining TTS chunks
   - Set `is_speaking = False`
   - Process the new utterance normally
3. Twilio's `mark` event can optionally confirm when audio finishes playing

**Reasoning:**
- Standard approach in production voice AI (Vapi, Retell, etc. all do this)
- Twilio's `clear` event is purpose-built for this — no hack needed
- Prevents the "talking over each other" feeling that makes voice AI feel robotic
- Simple state tracking — just a boolean flag

**Consequences:**
- Natural conversational feel — patient can interrupt at any time
- Interrupted responses are lost (patient's new input takes priority)
- Need to handle edge case: very short interruptions (cough, "um") shouldn't cancel the response — Deepgram's endpointing helps filter these

---

## ADR-027: Greeting — Pre-generate and Cache at Startup

**Context:** When a patient calls, the first thing they hear is a greeting ("Hello! Thank you for calling Sunshine Dental..."). We can generate this live via TTS on each call, or pre-generate it once.

**Decision:** Pre-generate greeting audio via ElevenLabs at app startup. Store as bytes in memory. Play instantly on call connect.

**Reasoning:**
- The greeting text is always the same — no reason to pay for TTS on every call
- Instant playback (~0ms) vs 500-800ms TTS latency on first impression
- First impression matters — immediate greeting feels professional and responsive
- Saves ElevenLabs API calls and character quota (important on free tier: 10k chars/month)

**Implementation:**
- On app startup: call ElevenLabs TTS with greeting text, format `ulaw_8000`, store result bytes
- On call connect: base64-encode cached bytes and send to Twilio immediately
- If startup generation fails: fall back to live generation on first call

**Consequences:**
- Instant greeting on every call
- One extra ElevenLabs API call on server startup (negligible)
- Greeting text changes require app restart (acceptable — it rarely changes)
- Saves ~50 characters per call from ElevenLabs quota

---

## ADR-028: Voice Pipeline Architecture — Call Session Pattern

**Context:** The voice pipeline needs to manage multiple concurrent async connections per call (Twilio WebSocket, Deepgram WebSocket, ElevenLabs HTTP streaming) plus shared state (is_speaking, stream_sid). We need to decide where orchestration and state live.

**Options considered:**

1. **Module-per-service** — Separate files per external service + a `pipeline.py` orchestrator. Problem: the orchestrator becomes a god object holding all state; interruption handling is awkward because STT events need to cancel TTS playback across module boundaries.

2. **Call Session pattern** (chosen) — A `CallSession` class that owns the full lifecycle of one phone call. Service wrappers (STT, TTS) are stateless. State and orchestration live in one place per call.

3. **Event-driven with async queues** — Each stage is a producer/consumer connected by `asyncio.Queue`. Elegant at scale but over-engineered for a single-server demo; interruption requires flushing multiple queues.

**Decision:** Call Session pattern (Option 2).

**File structure:**
```
app/voice/
  routes.py           # Thin FastAPI routes: POST /twilio/incoming, WS /twilio/media-stream
  call_session.py     # CallSession: one call's lifecycle, state, pipeline orchestration
  stt.py              # DeepgramSTT: stateless streaming STT wrapper
  tts.py              # ElevenLabsTTS: stateless streaming TTS wrapper + greeting cache
```

**Why this works:**
- **Natural state scoping** — Everything for one call (WebSocket refs, is_speaking flag, stream_sid, Deepgram connection) lives in one `CallSession` object
- **Interruption is simple** — The session sees both STT input and TTS output, so it can stop TTS when STT detects speech (no cross-module coordination)
- **Service wrappers are swappable** — Replace Deepgram with Google STT or ElevenLabs with another TTS without touching session logic
- **routes.py stays thin** — Just creates a `CallSession` and delegates; no business logic in route handlers

**Concurrency capacity:**
- Each active call holds one `CallSession` in memory (~few KB of state + audio buffers)
- Bottleneck is async I/O, not CPU — Python's asyncio handles concurrent WebSocket connections well
- A single FastAPI server can comfortably handle **10-50 concurrent calls** depending on memory and network
- For hundreds+ concurrent calls: move to Option 3 (event-driven with queues) or distribute across multiple server instances

**Consequences:**
- `CallSession` could grow large if not disciplined — keep service logic in stt.py/tts.py, only orchestration in session
- One object per call means state cleanup on disconnect is straightforward
- Scaling path is clear: horizontally (more servers) or architecturally (migrate to event-driven)

---

## ADR-029: Voice-Specific System Prompt

**Context:** First test call revealed the agent was too verbose for phone — responses designed for chat (multiple sentences, bullet points, tips) feel like a lecture over the phone. The system prompt in `prompts.py` was shared across all channels.

**Decision:** Add a `VOICE_ADDENDUM` to the system prompt when `channel == "voice"`. Thread the channel from the session DB record through `process_message()` → `build_system_prompt()`.

**Voice addendum rules:**
- Every response must be 1-2 short sentences max
- No markdown, bullet points, numbered lists, or formatting
- Present options conversationally, not as lists
- Do not give tips or instructions on how to provide information — just wait patiently
- If partial input is received (single digits, short words), just wait
- Keep confirmations brief

**Reasoning:**
- Voice and chat have fundamentally different constraints — voice needs brevity, chat allows detail
- The system prompt is the simplest lever — no code architecture change needed
- The session already stores `channel` in the DB, so detection is free
- Addendum approach preserves the full base prompt for chat/test channels

**Consequences:**
- `build_system_prompt()` accepts a `channel` parameter (default: "chat")
- `process_message()` reads `session["channel"]` and passes it through
- ~150 extra tokens in voice system prompt (negligible cost)
- Voice responses are dramatically shorter and more natural

---

## ADR-030: Smart Transcript Accumulation

**Context:** First test call revealed the agent was talking over the patient during phone number dictation. Deepgram's endpointing (300ms) would fire after each digit, producing individual transcripts ("4", "0", "2"). Each triggered `_on_transcript` → `process_message()`, and the agent responded to each digit with unhelpful advice about how to dictate numbers.

**Decision:** Buffer short transcripts in `CallSession` with a 1.5-second silence timeout. Flush immediately for substantial input (4+ words).

**Algorithm:**
1. Transcript arrives → append to `_utterance_buffer`
2. If word count >= 4: flush buffer immediately (full sentence — send to agent)
3. If word count < 4: start/reset a 1.5s `asyncio` timer
4. When timer fires (patient went quiet): join all buffered text, send as one message to agent
5. If new transcript arrives before timer: cancel timer, add to buffer, re-evaluate

**Reasoning:**
- Normal conversation (4+ words) is unaffected — processed immediately with zero added latency
- Digit-by-digit dictation (1-2 words each) accumulates naturally into one message
- 1.5s timeout is long enough to accumulate digits but short enough to feel responsive
- 4-word threshold covers the vast majority of real conversational sentences
- No Deepgram configuration changes needed — the fix is entirely in our layer

**Trade-offs considered:**
- Increasing Deepgram endpointing (from 300ms to 1500ms): simpler but adds latency to ALL responses
- Letting the agent handle it via prompt: unreliable — Claude might still respond to fragments

**Consequences:**
- `CallSession` gains `_utterance_buffer` (list) and `_buffer_timer` (asyncio.Task)
- Adds ~1.5s latency only for short utterances (digits, "yes", "no")
- Phone number dictation works naturally — all digits arrive as one message
- The buffer timer runs as an asyncio background task; cancelled on new input or call end

---

## ADR-031: Filler Phrases While Agent Is Thinking

**Context:** Test calls revealed noticeable silence (2-8 seconds) while the agent processes, especially for tool-calling turns (check_availability + book_appointment). The caller has no feedback that the system is working — feels like a dead line.

**Decision:** Pre-generate 4 filler phrases at startup (like the greeting). During processing, launch a fire-and-forget asyncio task that plays a random filler if the agent hasn't responded within 1.5 seconds. Cancel the task when the agent responds.

**Filler phrases:**
- "Let me check on that for you."
- "One moment, please."
- "Sure, let me look that up."
- "Let me see what we have available."

**Implementation:**
- `tts.py`: `generate_fillers()` pre-generates all 4 at startup (sequential to avoid rate limits), `get_random_filler()` returns one randomly
- `call_session.py`: `_play_filler_after_delay()` sleeps 1.5s then sends cached audio to Twilio. Created as `asyncio.create_task()`, cancelled via `filler_task.cancel()` when agent responds.
- `main.py`: calls `tts.generate_fillers()` in lifespan startup

**Reasoning:**
- Pre-cached audio plays instantly (0ms latency) — just send bytes to Twilio
- 1.5s delay means fast responses (simple FAQ) play without filler — no unnecessary noise
- Fire-and-forget pattern is simple: create task, cancel on completion
- ~120 characters total for 4 phrases — negligible ElevenLabs quota impact
- Mimics real receptionist behavior ("Let me check..." while looking something up)

**Consequences:**
- 4 extra ElevenLabs API calls at startup (~2s added to startup time)
- ~45KB of cached audio in memory (negligible)
- Fillers play on ~60% of turns (those involving tool calls)
- Sequential generation avoids ElevenLabs free-tier rate limits (429s on parallel requests)

---

## ADR-032: Farewell Detection

**Context:** Test calls revealed two issues with call endings: (1) "No thank you" after booking caused a 15-22 second silence while the agent processed, and (2) the agent sometimes re-processed the farewell incorrectly. Common farewells are predictable and don't need agent processing.

**Decision:** Check transcripts against a farewell regex before sending to the agent. Matching farewells skip the agent entirely and play a canned TTS response immediately.

**Farewell patterns matched:**
- "No thank you" / "No thanks"
- "No, I'm good" / "No, that's all" / "No, that's it"
- "That's all" / "That's it"
- "Goodbye" / "Bye"
- "Have a good/great/nice day"
- "See you" / "Nothing else"

**Canned response:** "Thank you for calling Sunshine Dental! Have a great day. Goodbye!"

**Strict regex design:** The regex must NOT match conversational phrases that happen to start with farewell words. For example, "No. That's too early. How about the afternoon?" must NOT trigger farewell detection. The regex requires farewell-specific endings (e.g., `that's all/it` not just `that's`), and anchors to end-of-string.

**Reasoning:**
- Farewells are the most predictable conversational pattern — high-confidence regex match
- Skipping the agent saves 2-8 seconds of processing + API cost
- The canned response is natural and consistent
- In practice, the agent handles farewells well too (personalized goodbye), so the regex is really a fast-path optimization — if it doesn't match, the agent handles it gracefully

**Consequences:**
- ~0ms response time for farewells (vs 2-8s through agent)
- Farewell response is not personalized (no "See you Tuesday!")
- False negatives are fine — the agent handles farewells naturally
- False positives are bad — must be tested thoroughly (the regex was refined after a false positive on "No. That's too early")

---

## ADR-033: Past Slot Filtering in Availability

**Context:** First test call offered "today at 8 AM" when it was already past 8 AM in the practice's timezone. `_compute_slots_for_day()` generated all slots within working hours without checking if they were in the past.

**Decision:** Add a `datetime.now(tz)` check in `_compute_slots_for_day()` — skip any slot that starts before the current time in the practice's local timezone.

**Implementation:** Three lines added to `_compute_slots_for_day()` in `scheduling.py`:
```python
now = datetime.now(tz)
# ... in the loop:
if current < now:
    current += timedelta(minutes=30)
    continue
```

**Reasoning:**
- Past appointments cannot be booked — offering them wastes a conversational turn
- The fix is in the data layer (guaranteed correct) rather than the prompt (unreliable)
- Uses practice-local time via `datetime.now(tz)` where `tz` comes from the date parameter's tzinfo
- Only affects "today" — future dates are unaffected since `now` is always less than tomorrow's slots

**Consequences:**
- `_compute_slots_for_day` is no longer a pure function (depends on current time)
- Tests that run on "today" dates may see different results depending on time of day
- Edge case: a slot starting 1-2 minutes from now is technically bookable but would be impractical — acceptable for a demo

---

## ADR-034: Concurrent Processing Lock

**Context:** Test calls revealed a race condition: if two Deepgram transcripts arrived in quick succession (e.g., from speech_final + UtteranceEnd, or from interruption + new speech), both could call `process_message()` concurrently on the same session. This caused the agent to see stale state or re-process actions.

**Decision:** Add an `asyncio.Lock` to `CallSession` that serializes transcript processing. Only one transcript can be in the `_process_and_speak` → agent → TTS pipeline at a time.

**Implementation:**
```python
self._processing_lock = asyncio.Lock()

# In _flush_buffer:
async with self._processing_lock:
    await self._process_and_speak(full_text)
```

**Reasoning:**
- `asyncio.Lock` is the standard Python mechanism for serializing coroutines
- The lock scope covers the entire process-and-speak cycle (agent call + TTS streaming)
- While locked, new transcripts still accumulate in the buffer (smart accumulation continues)
- When the lock releases, the next buffered transcript is processed
- Combined with smart accumulation (ADR-030), this means the patient's speech during agent processing is collected and sent as one message when the lock releases

**Consequences:**
- No concurrent agent calls per session — eliminates race conditions
- If the agent is slow, the patient's next utterance waits (but the filler phrase covers the perceived delay)
- Lock is per-CallSession, not global — different calls process independently
- Lock is released even on exception (via `async with` context manager)

---

## ADR-035: Error Handling, Silence Detection & Latency Logging

**Context:** The voice pipeline works end-to-end but lacks resilience. If the patient goes silent, nothing happens. If Deepgram disconnects or ElevenLabs fails mid-call, the patient hears silence with no recovery. We also have no visibility into per-stage latency. ADR-009 defined the tiered fallback table — this ADR implements the remaining items.

**Decision:** Three mechanisms plus latency instrumentation.

### 1. Silence Detection

Start a silence timer after the agent finishes speaking (patient's "turn"). Reset on any transcript. Two thresholds:

| Threshold | Action |
|-----------|--------|
| 20 seconds | Play "Are you still there? I'm here to help if you need anything." |
| 30 seconds | Play "It seems we got disconnected. Goodbye!" and end the call (4s delay before closing to let Twilio play the audio). |

Timer starts when `_speak()` completes. Resets on any `_on_transcript` call. Cancelled while the agent is speaking (`is_speaking = True`). Uses an asyncio task that sleeps and checks elapsed time.

**Why start after speaking, not always?**
- If the timer ran during agent speech, it could fire while we're still talking — a false positive.
- The patient isn't expected to speak while the agent is speaking, so silence during TTS is not meaningful.

### 2. Deepgram Connection Drop

If Deepgram's WebSocket dies (connection error, unexpected close):
- Play a pre-cached error audio clip: "We're experiencing technical difficulties. Please try calling back in a moment."
- End the call gracefully (close Twilio stream, clean up session).
- No auto-reconnect — adds complexity for a rare edge case in a demo.

**Implementation:** Add error/close handling in `DeepgramSTT` that invokes an `on_error` callback on CallSession. CallSession plays the cached error clip and calls `stop()`.

### 3. ElevenLabs Failure

During a Twilio Media Stream, we cannot switch to `<Say>` TwiML. If `synthesize_stream()` fails:
- Play a pre-cached error audio clip (same clip as Deepgram fallback).
- The `_speak()` method already catches exceptions — enhance it to play the cached error clip instead of silently failing.

**Implementation:** Pre-cache an error message audio at startup (alongside greeting and fillers in `tts.py`). On TTS failure, CallSession plays the cached clip.

### 4. Latency Logging

Instrument the processing pipeline with `time.monotonic()` timestamps at each stage:

| Metric | Start → End |
|--------|-------------|
| `stt_to_flush_ms` | Last Deepgram transcript → `_flush_buffer()` entry |
| `agent_ms` | Before `process_message()` → after response |
| `tts_first_chunk_ms` | After agent response → first audio chunk sent to Twilio |
| `total_turn_ms` | `_flush_buffer()` entry → first audio chunk sent to Twilio |

Logged as a single structured line per turn at INFO level.

**Consequences:**
- Silence detection prevents zombie calls that rack up Twilio minutes
- Pre-cached error clip provides graceful degradation for both STT and TTS failures (~1 extra ElevenLabs API call at startup)
- Latency logs enable diagnosing slow turns without adding external monitoring
- All three mechanisms are self-contained in `CallSession` — no changes to agent core

---

## ADR-036: Chat Widget & WebSocket Architecture

**Context:** Phase 3 adds a browser-based chat widget that connects to the same Agent Core via WebSocket. We need to decide on backend module structure, widget packaging, keepalive strategy, and reconnect behavior.

**Decision:** Six sub-decisions for the chat transport layer.

### 1. Backend Module Structure

New `app/chat/routes.py` module with its own `APIRouter`, registered in `main.py` — mirrors the `app/voice/routes.py` pattern.

**Why:** Keeps each transport channel in its own module. The voice module already established this convention.

### 2. Widget Packaging — Single File

One `widget.js` file in `app/widget/` served via FastAPI `StaticFiles` mount at `/widget/`. CSS is embedded as a template literal inside the JS and injected into the Shadow DOM.

**Why:** A single `<script>` tag with zero extra HTTP requests is the standard pattern for embeddable widgets (Intercom, Drift, etc.). Eliminates CORS and load-order issues.

### 3. Application-Level Ping/Pong

Client sends `{"type": "ping"}` every 30 seconds. Server responds `{"type": "pong"}`. Server closes the connection after 60 seconds with no ping.

**Why:** Native WebSocket ping/pong frames are unreliable across proxies and load balancers. Application-level messages give us explicit control and are already defined in the CHAT_WIDGET.md protocol spec.

### 4. Auto-Reconnect — Exponential Backoff

On disconnect, the widget reconnects with exponential backoff: 1s → 2s → 4s → 8s → … → max 30s. After 10 failed attempts, show a "Connection lost" message with a manual retry button. No unsent message queue — the user can see the disconnection and resend.

**Why:** Standard, simple, effective. A message queue adds complexity for a rare edge case.

### 5. Chat Channel Value

Chat widget sessions use `channel="chat"`, which is the existing default. The agent system prompt already produces longer, markdown-friendly responses for non-voice channels.

**Why:** The existing prompt behavior is correct for chat. No new channel type needed.

### 6. Keep Temporary `/chat/test` Endpoint

The POST `/chat/test` endpoint from Phase 2 remains alongside the new WebSocket endpoint. Useful for quick `curl` testing without spinning up a widget.

**Why:** Zero maintenance cost, helpful for debugging. Clean up in Phase 6.

**Consequences:**
- `app/chat/` mirrors `app/voice/` — predictable project structure
- Single-file widget is easy to embed but CSS changes require editing JS (acceptable for a demo)
- Application-level keepalive adds minor bandwidth (~1 small JSON message per 30s per connection)
- Exponential backoff prevents reconnect storms under network issues

---

## ADR-037: Email Notifications via SendGrid

**Context:** After booking, cancelling, or rescheduling an appointment, patients and providers have no confirmation outside of the conversation itself. Adding notifications makes the demo feel like a complete workflow — an interviewer could book via voice/chat and receive a real email confirmation. SMS was considered but rejected because the developer is in Colombia; international SMS from a US Twilio number costs ~$0.0375/message vs free email.

**Decision:** Use SendGrid (free tier) for email notifications on booking, cancellation, and rescheduling. Send to both the patient and the provider.

**Reasoning:**
- **SendGrid free tier** — 100 emails/day, $0/month. More than enough for a demo.
- **Twilio-owned** — ecosystem alignment with existing Twilio account, though requires a separate free signup.
- **Email > SMS for this project** — developer is in Colombia, international SMS is expensive and unreliable. Email is free and works globally.
- **Both recipients** — patient gets confirmation of their appointment; provider gets a heads-up. Demonstrates a real-world notification flow.
- **Fire-and-forget** — notification failures should not block the agent response. Log errors, don't retry.

**Implementation plan (Phase 4.5):**

### 1. Data Changes
- Add `email` column to `providers` table (migration). Populate with developer's real email for mock providers.
- Agent already collects patient name and phone during booking. Add **patient email** as a collected field — agent asks for it during the booking flow.
- Update `book_appointment` tool schema to accept `patient_email` parameter.

### 2. Notification Service
- New `app/notifications/email_service.py` — wraps SendGrid Python SDK.
- `send_booking_confirmation(patient_email, provider_email, appointment_details)` — HTML email with practice name, provider, date/time, procedure.
- `send_cancellation_notice(patient_email, provider_email, appointment_details)` — confirmation of cancellation.
- `send_reschedule_notice(patient_email, provider_email, old_time, new_time, appointment_details)` — shows old → new time.
- All emails include "Demo — Not HIPAA Compliant" disclaimer in footer.

### 3. Integration
- Called from `tools.py` after successful `book_appointment`, `cancel_appointment`, `reschedule_appointment`.
- Fire-and-forget: wrap in try/except, log errors, never block the agent response.
- New env vars: `SENDGRID_API_KEY`, `NOTIFICATION_FROM_EMAIL`.

### 4. Email Templates
- Simple HTML templates with inline CSS (email client compatibility).
- Practice branding (name, phone, address in footer).
- Bilingual support: detect session language and send email in matching language.

**Consequences:**
- New external dependency: SendGrid account + API key + `sendgrid` Python package.
- Agent flow changes slightly: must collect patient email during booking (one extra question).
- Provider email in DB schema — minor migration.
- Email delivery is best-effort — no retry queue, no delivery tracking (appropriate for a demo).
- Adds strong "wow factor" to live demos — tangible proof the system works end-to-end.

---

## ADR-038: Admin Dashboard — Session Metrics, Calendar View & Rich Analytics

**Context:** Phase 5 adds an admin dashboard for reviewing agent activity. The initial plan was a simple table-based list view with basic counts. After discussion, we decided to build a more comprehensive dashboard: full conversation log viewer with per-session performance metrics, a Google Calendar-style appointment view, and richer analytics.

**Decision:** Three major sub-decisions.

### 1. Session Metrics — Persist Performance Data to DB

We already compute latency metrics in `call_session.py` (`agent_ms`, `tts_first_chunk_ms`, `total_turn_ms`) and log them to stdout. We also have timing in `chat/routes.py` (agent processing time). Instead of only logging, we persist these metrics to the database.

**Implementation:**
- New migration: add `metrics JSONB` column to `sessions` table (default `{}`)
- Metrics stored per session (accumulated across turns):
  - `total_turns` — number of user→agent exchanges
  - `avg_agent_ms` — average agent response time
  - `avg_tts_first_chunk_ms` — average TTS first-chunk latency (voice only)
  - `avg_total_turn_ms` — average end-to-end turn latency (voice only)
  - `tools_used` — list of tool names invoked during session
  - `appointment_booked` — boolean, whether an appointment was booked
  - `outcome` — "completed" (patient said goodbye), "abandoned" (silence timeout), "error" (crash)
- Updated in `call_session.py` after each turn and on session end
- Updated in `chat/routes.py` after each message exchange
- Changes are minimal: wrap existing metric values in a dict, write to DB alongside existing logger calls

**Why JSONB:** Schema-free — we can add new metrics without migrations. Metrics are read-only in the dashboard, never queried with WHERE clauses, so no need for indexed columns.

### 2. Appointments — Full Calendar View

Build a Google Calendar-style visual schedule with:
- **Day view** (default): one column per provider, time slots as rows (8 AM – 5 PM)
- **Week view**: 7 columns (one per day), appointments as colored blocks
- Provider filter: show/hide individual providers
- Date navigation: prev/next day/week, "today" button
- Click an appointment block to see details (patient, procedure, status, booked via)
- Color coding: by provider (day view) or by procedure type (week view)
- Cancelled appointments shown as faded/strikethrough

**Why full calendar over a simple table:** This is a portfolio project for an "AI Agent Builder" role. A calendar view demonstrates frontend capability and makes the dashboard feel like a real practice management tool. The appointments table already has all the data needed — `starts_at`, `duration_minutes`, `provider_id` — to render time blocks.

**Implementation approach:**
- Pure vanilla JS + CSS (no calendar library) — keeps it zero-dependency, demonstrates skill
- CSS Grid for the time/provider grid layout
- Appointments fetched from `/admin/api/appointments` with date range filter
- Provider list fetched from a new `/admin/api/providers` endpoint (or inline in the page)

### 3. Stats — Rich Analytics

Beyond basic counts, the stats section shows:
- **Today's summary:** total sessions, voice vs chat breakdown, appointments booked/cancelled, avg session duration
- **All-time totals:** total sessions, total appointments booked
- **Language breakdown:** English vs Spanish sessions (percentage)
- **Channel breakdown:** voice vs chat over time
- **Busiest day of week:** which weekday has the most sessions
- **Most common procedures:** top procedure types booked
- **Average response latency:** from session metrics (voice only)

All computed via SQL aggregate queries — no pre-computation needed.

### 4. Frontend Approach — Single Static HTML File with Tailwind CDN

The dashboard is a single `app/admin/dashboard.html` file served from `GET /admin/`. Uses Tailwind CDN (`<script src="https://cdn.tailwindcss.com">`) + Google Fonts (Inter + Material Symbols Outlined) for styling. Contains embedded JS. Fetches data from `/admin/api/*` endpoints via `fetch()`.

**Why Tailwind CDN instead of vanilla CSS:** We used AI design tools to generate visual references (see 4b). Translating hundreds of Tailwind utility classes to vanilla CSS would be error-prone and slow. Tailwind CDN is a single `<script>` tag — no build step, no npm — same deployment simplicity as vanilla CSS with much faster implementation from the reference designs.

**Why not Jinja2:** No server-side rendering dependencies. The widget already established the "self-contained HTML/JS that calls APIs" pattern. The dashboard is a client-side SPA with tab navigation.

### 4b. Design Process — AI-Assisted Visual Design

The dashboard visual design was created using two AI design tools:

1. **Google Stitch** — generated three HTML mockup screens (Sessions, Appointments calendar, Analytics) from a detailed design prompt describing layout, components, and aesthetic goals
2. **v0 (Vercel)** — generated a full React + Tailwind + shadcn/ui reference implementation with component structure, design tokens, and mock data (stored in `reference-design/` for reference)

We preferred the v0 component designs and used those as the primary reference. The implementation extracted the design system (colors, spacing, typography, component patterns) from the v0 code and translated it to a single vanilla HTML/JS file using Tailwind CDN.

**Why this approach:** Neither the developer nor the AI coding agent are visual designers. Using AI design tools for the visual layer and an AI coding agent for the implementation produced a professional-looking dashboard without design expertise. The v0 reference code provided exact color values, spacing, and component structure — eliminating guesswork.

### 5. UI Structure — Tabbed SPA

Three tabs:
- **Sessions** — list of sessions (most recent first) with drill-down to conversation viewer
- **Appointments** — calendar view (day/week toggle)
- **Analytics** — stats cards + charts

### 6. No Authentication

This is a demo project. The "Demo — Not HIPAA Compliant" disclaimer covers it. Basic auth can be added later.

**Consequences:**
- New migration for `metrics` JSONB column on sessions
- Minor instrumentation changes in `call_session.py` and `chat/routes.py` (persist metrics that are already computed)
- Calendar view is the most complex frontend component — will require dedicated implementation effort
- Dashboard is self-contained (single HTML file) — no build step, no framework dependencies
- Analytics queries may be slow on very large datasets — acceptable for a demo with <1000 sessions
- No real-time updates (manual refresh) — sufficient for a demo dashboard

---

## ADR-039: TTS Provider Swap — ElevenLabs → Deepgram Aura

**Context:** During Phase 5 development, the ElevenLabs free tier (10,000 characters/month) was exhausted with only 17 characters remaining — not enough for even a single voice call. The API key also had its permissions silently restricted by an ElevenLabs platform update, causing 401 errors that required manual permission re-grants. We needed TTS working immediately to test voice call metrics in the new admin dashboard.

**Decision:** Replace ElevenLabs with Deepgram Aura TTS.

**Reasoning:**
- **Already in the stack** — Deepgram is already used for STT (Nova-2). Same account, same API key, $200 free credit barely touched.
- **mulaw support** — Deepgram Aura supports `encoding=mulaw&sample_rate=8000&container=none`, producing raw mulaw bytes identical to what ElevenLabs provided. Zero changes needed to the audio pipeline (call_session.py, routes.py, Twilio integration).
- **Cost** — $0.015 per 1K characters. With $200 credit, that's ~13 million characters. ElevenLabs Starter plan would have been $5/mo for 30K characters.
- **Simpler stack** — One fewer vendor. STT and TTS from the same provider.
- **Streaming** — Deepgram supports HTTP streaming responses (`Transfer-Encoding: chunked`), so the existing stream-chunks-to-Twilio pattern works unchanged.

**What changed:**
- `app/voice/tts.py` — Complete rewrite. Replaced ElevenLabs SDK with direct `httpx` calls to Deepgram's `/v1/speak` endpoint. Same public API (same function signatures, same return types).
- `app/config.py` — `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` are no longer used at runtime. `DEEPGRAM_API_KEY` (already configured) is now used for both STT and TTS.
- No changes to `call_session.py`, `routes.py`, `stt.py`, or any other module.

**Voice model:** `aura-asteria-en` — a female English voice that also handles Spanish text acceptably.

**What did NOT change:**
- Audio format: still raw mulaw/8000 bytes
- Streaming pattern: still async iterator yielding chunks
- Caching pattern: greeting, fillers, error clip still pre-generated at startup
- All function signatures: `synthesize_stream()`, `generate_greeting()`, `get_cached_greeting()`, etc. — identical API

**Consequences:**
- ElevenLabs is no longer a runtime dependency (SDK can be removed from requirements.txt)
- Voice quality is different — Deepgram Aura is functional but less natural than ElevenLabs' multilingual v2. Acceptable for a demo.
- No more voice ID configuration needed — the model name is hardcoded
- Bilingual support is weaker — Aura handles Spanish text but with an English accent. ElevenLabs' multilingual model was better at code-switching. For a demo, this is acceptable.
