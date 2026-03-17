# API Reference

All HTTP and WebSocket endpoints exposed by the FastAPI backend.

---

## Base URL

- **Local:** `http://localhost:8000`
- **Production:** `https://your-app.railway.app` (TBD after deployment)

---

## Health & Status

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "active_sessions": 3
}
```

---

## Twilio Voice Endpoints

### `POST /twilio/incoming`

Webhook called by Twilio when a call comes in. Returns TwiML to initiate a Media Stream.

**Headers:**
- Standard Twilio webhook headers (validated with Twilio signature)

**Request Body (form-encoded by Twilio):**
- `CallSid` — Unique call identifier
- `From` — Caller phone number
- `To` — Your Twilio number
- `CallStatus` — "ringing"

**Response (TwiML XML):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://your-server.com/twilio/media-stream">
      <Parameter name="session_id" value="uuid" />
    </Stream>
  </Connect>
</Response>
```

### `POST /twilio/status`

Webhook for call status updates (optional, for logging).

**Request Body:**
- `CallSid`
- `CallStatus` — "completed", "failed", "busy", "no-answer"
- `CallDuration` — Duration in seconds

---

### `WS /twilio/media-stream`

WebSocket endpoint for Twilio Media Streams. This is where real-time audio flows.

**Protocol:** See [VOICE_PIPELINE.md](./VOICE_PIPELINE.md) for full details.

**Inbound events from Twilio:**
- `connected` — Stream connected
- `start` — Stream started (contains streamSid, callSid)
- `media` — Audio data (base64 mulaw)
- `stop` — Stream ended

**Outbound events to Twilio:**
- `media` — Audio data to play
- `clear` — Clear queued audio
- `mark` — Mark event for tracking playback position

---

## Chat Endpoints

### `WS /chat/ws`

WebSocket endpoint for the chat widget.

**Query Parameters:**
- `practice_id` (optional) — Practice identifier (default: "default")

**Client → Server messages:**
```json
{"type": "message", "content": "string", "session_id": "string|null"}
```
```json
{"type": "ping"}
```

**Server → Client messages:**
```json
{"type": "welcome", "content": "string", "session_id": "string"}
```
```json
{"type": "message", "content": "string", "session_id": "string"}
```
```json
{"type": "typing", "status": true|false}
```
```json
{"type": "error", "content": "string"}
```
```json
{"type": "pong"}
```

---

## Admin Dashboard Endpoints (Phase 5 — ADR-038)

> **Not yet implemented.** These endpoints are designed and will be built in Phase 5.

### `GET /admin/`

Serves the admin dashboard HTML page (single static file with embedded CSS/JS).

### `GET /admin/api/sessions`

List all sessions with summary info.

**Query Parameters:**
- `active_only` (bool, default: false) — Only return active sessions
- `limit` (int, default: 50) — Max results
- `offset` (int, default: 0) — Pagination offset

**Response:**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "channel": "voice|chat",
      "started_at": "2025-01-15T10:30:00Z",
      "ended_at": "2025-01-15T10:35:00Z",
      "status": "active|ended",
      "language": "en|es",
      "caller_number": "+16195551001",
      "message_count": 8,
      "metrics": {
        "total_turns": 4,
        "avg_agent_ms": 1200,
        "avg_total_turn_ms": 2100,
        "tools_used": ["check_availability", "book_appointment"],
        "appointment_booked": true,
        "outcome": "completed"
      }
    }
  ],
  "total": 42
}
```

### `GET /admin/api/sessions/{session_id}`

Get full session detail including conversation history and performance metrics.

**Response:**
```json
{
  "id": "uuid",
  "channel": "voice",
  "started_at": "2025-01-15T10:30:00Z",
  "ended_at": "2025-01-15T10:35:00Z",
  "status": "ended",
  "language": "en",
  "caller_number": "+16195551001",
  "messages": [
    {
      "role": "assistant",
      "content": "Hello! Thank you for calling...",
      "timestamp": "2025-01-15T10:30:01Z"
    },
    {
      "role": "user",
      "content": "I'd like to book an appointment",
      "timestamp": "2025-01-15T10:30:15Z"
    }
  ],
  "metrics": {
    "total_turns": 4,
    "avg_agent_ms": 1200,
    "avg_tts_first_chunk_ms": 350,
    "avg_total_turn_ms": 2100,
    "tools_used": ["check_availability", "book_appointment"],
    "appointment_booked": true,
    "outcome": "completed"
  }
}
```

### `GET /admin/api/appointments`

List appointments for calendar rendering or table view.

**Query Parameters:**
- `date_from` (str, optional) — Start of date range (YYYY-MM-DD). Defaults to today.
- `date_to` (str, optional) — End of date range (YYYY-MM-DD). Defaults to `date_from`.
- `provider_id` (str, optional) — Filter by provider
- `status` (str, optional) — Filter by status (confirmed, cancelled)
- `search` (str, optional) — Search by patient name (partial match)

**Response:**
```json
{
  "appointments": [
    {
      "id": "apt_001",
      "patient_name": "John Smith",
      "patient_phone": "(619) 555-1001",
      "provider_id": "prov_001",
      "provider_name": "Dr. Sarah Chen",
      "starts_at": "2025-01-20T09:00:00-08:00",
      "duration_minutes": 30,
      "appointment_type": "Exam",
      "status": "confirmed",
      "booked_via": "voice",
      "created_at": "2025-01-15T10:34:00Z"
    }
  ],
  "total": 15
}
```

### `GET /admin/api/providers`

List providers (for calendar column headers and filter dropdowns).

**Response:**
```json
{
  "providers": [
    {
      "id": "prov_001",
      "name": "Dr. Sarah Chen",
      "specialty": "General Dentistry",
      "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "working_hours": {"start": "09:00", "end": "17:00"}
    }
  ]
}
```

### `GET /admin/api/stats`

Rich analytics — summary statistics and breakdowns.

**Response:**
```json
{
  "today": {
    "total_sessions": 12,
    "voice_sessions": 8,
    "chat_sessions": 4,
    "appointments_booked": 5,
    "appointments_cancelled": 1,
    "avg_session_duration_seconds": 180
  },
  "all_time": {
    "total_sessions": 156,
    "appointments_booked": 67
  },
  "language_breakdown": {
    "en": 140,
    "es": 16
  },
  "busiest_day_of_week": "Tuesday",
  "top_procedures": [
    {"name": "Cleaning", "count": 28},
    {"name": "Exam", "count": 15},
    {"name": "Root Canal", "count": 8}
  ],
  "avg_agent_latency_ms": 1150
}
```

---

## Widget Static Files

### `GET /widget/widget.js`

Serves the embeddable chat widget (self-contained JS with CSS embedded in Shadow DOM).

### `GET /widget/test.html`

Standalone test page for the widget.

### `GET /widget/test-wordpress.html`

WordPress-like test page with aggressive CSS conflicts for Shadow DOM isolation testing.

---

## Error Response Format

All API errors follow this format:

```json
{
  "error": {
    "code": "session_not_found",
    "message": "Session with ID xyz does not exist"
  }
}
```

Common error codes:
- `session_not_found` — Invalid session ID
- `invalid_request` — Malformed request body
- `rate_limited` — Too many requests
- `internal_error` — Unexpected server error
