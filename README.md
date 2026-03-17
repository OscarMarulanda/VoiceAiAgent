# VoiceAiAgent

AI-powered voice and chat agent for healthcare practices — handles appointment booking, FAQs, and rescheduling via phone (Twilio + Deepgram) and web chat, with bilingual English/Spanish support.

## What It Does

- **Book appointments** — checks provider availability, detects scheduling conflicts, confirms bookings
- **Answer FAQs** — practice hours, accepted insurance, provider info, location/directions
- **Reschedule & cancel** — looks up existing appointments by patient info
- **Bilingual** — responds in English or Spanish based on caller preference
- **Email confirmations** — sends booking/cancellation/rescheduling notifications via SendGrid

## Architecture

Two interfaces, one brain — the same agent logic serves both channels:

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

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| AI | Claude API (Anthropic) with tool calling |
| Speech-to-Text | Deepgram Nova-2 (streaming) |
| Text-to-Speech | Deepgram Aura |
| Telephony | Twilio Voice + Media Streams |
| Database | PostgreSQL via asyncpg (raw SQL, no ORM) |
| Email | SendGrid |
| Chat Widget | Vanilla JS, Shadow DOM, WebSocket |
| Deployment | Railway + Supabase |

## Quick Start

```bash
# Clone
git clone https://github.com/OscarMarulanda/VoiceAiAgent.git
cd VoiceAiAgent

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Database
createdb voiceagent
psql voiceagent -f migrations/001_initial.sql

# Environment variables
cp .env.example .env
# Edit .env with your API keys (see docs/COSTS.md for where to get them)

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/health
```

## Project Structure

```
VoiceAiAgent/
├── app/
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Settings and env vars
│   ├── database.py         # asyncpg connection pool and query helpers
│   ├── agent/              # AI agent core (Claude + tools)
│   ├── voice/              # Twilio + Deepgram STT/TTS
│   ├── chat/               # WebSocket chat handler
│   ├── domain/             # Domain models and services
│   ├── repositories/       # DB access (asyncpg, raw SQL)
│   ├── mock_api/           # Mock practice data
│   ├── admin/              # Admin dashboard
│   └── widget/             # Embeddable chat widget (JS)
├── migrations/             # SQL migration scripts
├── tests/                  # Test suite
├── docs/                   # Documentation
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
└── Procfile                # Deployment start command
```

## How It Works

### Voice (Phone)

Patient calls a Twilio number → Twilio opens a Media Stream WebSocket to the backend → audio is streamed to Deepgram for real-time transcription → transcribed text goes to the Agent Core (Claude with tools) → Claude's response is sent to Deepgram Aura for TTS → audio is streamed back through Twilio to the caller. Supports interruption — if the patient speaks while the agent is responding, TTS stops immediately.

### Chat (Web Widget)

An embeddable `<script>` tag adds a chat widget to any website. The widget opens a WebSocket to the backend → patient messages go to the same Agent Core → text responses stream back. Session persists across page navigation via `sessionStorage`, with auto-reconnect on connection loss.

### Agent Core

The agent uses Claude with 9 tools (check availability, book/cancel/reschedule appointments, practice info, providers, insurance, appointment lookup, session notes). Conversation context uses a structured notepad (JSONB) + compact tool log + last 8 exchanges — not full history. Voice mode gets a short-response addendum to keep answers concise.

## Testing

```bash
# Run all tests
pytest

# Test agent logic interactively (no voice/chat needed, requires DB + API key)
python -m app.agent.test_cli              # chat mode
python -m app.agent.test_cli --channel voice  # voice mode (shorter responses)
```

## Deployment

Deployed on **Railway** (hosting) + **Supabase** (PostgreSQL). See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full setup instructions.

Estimated running cost for demo usage: **~$14–30/month**. See [docs/COSTS.md](docs/COSTS.md) for detailed breakdown.

## Documentation

| Document | Description |
|----------|-------------|
| [PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Goals, audience, success criteria |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flows |
| [ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) | ADRs for every tech choice |
| [VOICE_PIPELINE.md](docs/VOICE_PIPELINE.md) | Voice call handling in detail |
| [CHAT_WIDGET.md](docs/CHAT_WIDGET.md) | Chat widget design and integration |
| [MOCK_DATA.md](docs/MOCK_DATA.md) | Mock practice data schema |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | Endpoint documentation |
| [MODULES.md](docs/MODULES.md) | Module-by-module code guide |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, commands, debugging |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Railway + Supabase deployment |
| [COSTS.md](docs/COSTS.md) | Service costs and API keys |
| [CHECKLIST.md](docs/CHECKLIST.md) | Implementation progress tracker |

## Disclaimer

This is a **portfolio/demo project** — not a production system. It uses mock patient data, is **not HIPAA-compliant**, and is not intended for real medical scheduling. Built as a proof-of-concept for AI-powered practice management automation.
