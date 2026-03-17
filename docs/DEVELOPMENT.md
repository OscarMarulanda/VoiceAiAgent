# Development Guide

How to set up and run the project locally for development.

---

## Prerequisites

- **Python 3.13** — Using Homebrew (`/opt/homebrew/bin/python3.13`). 3.11+ should also work.
- **PostgreSQL** — Already installed and running locally
- **pip** or **uv** — Package manager
- **Git** — Version control
- **A code editor** — VS Code recommended
- **API keys** — See [COSTS.md](./COSTS.md) for where to get them

---

## Local Setup

### 1. Clone and enter the repo
```bash
cd /Users/oscarm/Documents/VoiceAiAgent
git init
```

### 2. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create local database
```bash
createdb voiceagent
# Apply migrations
psql voiceagent -f migrations/001_initial.sql
```

### 5. Create .env file
```bash
cp .env.example .env
# Edit .env with your API keys
# DATABASE_URL is pre-set for local Postgres:
# DATABASE_URL=postgresql://localhost/voiceagent
```

### 6. Run the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Verify
```bash
curl http://localhost:8000/health
```

---

## Project Structure

```
VoiceAiAgent/
├── app/                    # Application source code
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Settings and env vars
│   ├── database.py         # asyncpg connection pool and query helpers
│   ├── models/             # Pydantic data models
│   ├── agent/              # AI agent core
│   ├── voice/              # Twilio + Deepgram + ElevenLabs
│   ├── chat/               # WebSocket chat
│   ├── mock_api/           # Mock MacPractice API
│   ├── repositories/       # DB access (asyncpg, raw SQL)
│   ├── admin/              # Admin dashboard (Phase 5)
│   └── widget/             # Chat widget (JS/CSS)
├── migrations/             # SQL migration scripts
│   ├── 001_initial.sql     # Initial schema
│   ├── 002_session_context.sql  # Session context JSONB
│   ├── 003_practice_timezone.sql # Practice timezone column
│   ├── 004_appointment_updated_at.sql # Appointment updated_at + trigger
│   └── 005_session_metrics.sql # Session metrics JSONB column
├── tests/                  # Test files
├── docs/                   # Documentation (you are here)
├── .env                    # Environment variables (not in git)
├── .env.example            # Template for .env
├── .gitignore
├── requirements.txt
├── Procfile                # For deployment
└── README.md
```

---

## Development Workflow

### Running Tests
```bash
# All tests
pytest

# Specific module
pytest tests/test_scheduling.py

# With verbose output
pytest -v

# Only unit tests (skip integration)
pytest -m "not integration"
```

### Testing the Chat Widget Locally
1. Start the server: `uvicorn app.main:app --reload`
2. Open `http://localhost:8000/admin/` for the dashboard
3. Open the test page with embedded widget (served by FastAPI)
4. Or create a simple HTML file:
```html
<!DOCTYPE html>
<html>
<body>
  <h1>Test Page</h1>
  <script src="http://localhost:8000/widget/widget.js"
          data-server="http://localhost:8000"
          data-practice="Sunshine Dental"></script>
</body>
</html>
```

### Testing Voice Locally

Voice testing requires your server to be reachable by Twilio. Options:

**Option A: ngrok (recommended for dev)**
```bash
# In terminal 1: run the server
uvicorn app.main:app --reload --port 8000

# In terminal 2: expose via ngrok
ngrok http 8000
```
Then update Twilio webhook URL to the ngrok URL.

**Option B: Deploy to Railway and test there**

### Testing Agent Logic (No External APIs)
For quick iteration on the agent without voice/chat:
```bash
# Chat mode (default — longer, markdown-friendly responses)
python -m app.agent.test_cli

# Voice mode (short, 1-2 sentence responses)
python -m app.agent.test_cli --channel voice
```
This lets you type messages and see agent responses in the terminal. Requires the DB and `ANTHROPIC_API_KEY` in `.env`.

---

## Code Style

- **Formatter:** Black (default settings)
- **Linter:** Ruff
- **Type hints:** Use them for function signatures
- **Async:** Use `async/await` throughout — FastAPI is async-native
- **Imports:** Standard library → third-party → local, separated by blank lines

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `anthropic` | Claude API client |
| `deepgram-sdk` | Deepgram STT client |
| `elevenlabs` | ElevenLabs TTS client |
| `twilio` | Twilio helper library |
| `pydantic` | Data validation and models |
| `pydantic-settings` | Settings from environment |
| `python-dotenv` | Load .env files |
| `websockets` | WebSocket support (used by FastAPI) |
| `jinja2` | HTML templates (admin dashboard) |
| `pytest` | Testing |
| `pytest-asyncio` | Async test support |
| `httpx` | HTTP client for tests |
| `asyncpg` | Async PostgreSQL driver (raw SQL, no ORM) |

---

## Common Commands (Quick Reference)

All commands run from project root: `~/Documents/VoiceAiAgent`

### Server

```bash
# Start server
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start with auto-reload (restarts on file changes)
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Kill server
lsof -ti:8000 | xargs kill -9

# Kill and restart
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 1 && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/health
```

### ngrok Tunnel (required for voice calls)

```bash
# Start tunnel (separate terminal)
ngrok http 8000 --domain arie-euphotic-nonpictorially.ngrok-free.dev

# Verify tunnel
curl https://arie-euphotic-nonpictorially.ngrok-free.dev/health
```

**Twilio webhook:** `https://arie-euphotic-nonpictorially.ngrok-free.dev/twilio/incoming`
**Phone number:** +1 402 243 6878

### Logs

Logs print to the terminal where uvicorn is running. Useful grep patterns:

```bash
# Search for latency stats
grep "Latency" server.log

# Search for a specific session
grep "session_id=YOUR_ID" server.log

# Search for errors
grep -E "ERROR|Exception|Traceback" server.log

# Search for silence detection
grep "Silence detected" server.log

# Search for agent responses
grep "Agent response" server.log

# Search for transcripts
grep "Patient said" server.log
```

**Tip:** Run the server in a dedicated terminal for real-time log visibility. Don't run it in the background unless using Claude Code.

### Tests

```bash
# Run all tests (quick)
source .venv/bin/activate && python -m pytest tests/ -x -q

# Run all tests (verbose)
source .venv/bin/activate && python -m pytest tests/ -v

# Run a specific file
source .venv/bin/activate && python -m pytest tests/test_agent.py -v

# Run tests matching a keyword
source .venv/bin/activate && python -m pytest tests/ -k "booking" -v
```

### Database

```bash
# Open psql shell
psql voiceagent

# Latest appointments (Pacific time)
psql voiceagent -c "
SELECT patient_name, appointment_type, provider_id, status,
       starts_at AT TIME ZONE 'America/Los_Angeles' AS starts_local,
       created_at AT TIME ZONE 'America/Los_Angeles' AS created_local
FROM appointments ORDER BY created_at DESC LIMIT 10;
"

# Recent sessions
psql voiceagent -c "
SELECT id, channel, status, caller_number, started_at, ended_at
FROM sessions ORDER BY started_at DESC LIMIT 10;
"

# Run a migration
psql voiceagent -f migrations/001_initial.sql

# Re-seed mock data
source .venv/bin/activate && python -m app.seed
```

### Chat Test Endpoint (no voice needed)

```bash
# New session
curl -s -X POST http://localhost:8000/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, I want to book an appointment"}' | python -m json.tool

# Continue session
curl -s -X POST http://localhost:8000/chat/test \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_ID", "message": "A cleaning next Monday"}' | python -m json.tool
```

### Cheat Sheet

| Task | Command |
|------|---------|
| Start server | `source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Start ngrok | `ngrok http 8000 --domain arie-euphotic-nonpictorially.ngrok-free.dev` |
| Kill server | `lsof -ti:8000 \| xargs kill -9` |
| Run tests | `source .venv/bin/activate && python -m pytest tests/ -x -q` |
| Health check | `curl http://localhost:8000/health` |
| DB shell | `psql voiceagent` |
| Phone number | +1 402 243 6878 |

---

## Debugging Tips

- **FastAPI auto-docs:** Visit `http://localhost:8000/docs` for Swagger UI
- **WebSocket testing:** Use `websocat` CLI tool or browser dev tools
- **Twilio logs:** Check Twilio Console → Monitor → Logs
- **Claude API logs:** Log request/response in agent core for debugging prompts
- **Deepgram logs:** Enable debug logging in Deepgram SDK
- **Database:** Connect directly with `psql voiceagent` to inspect data
