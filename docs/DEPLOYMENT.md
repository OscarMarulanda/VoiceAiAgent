# Deployment

How to deploy the AI Voice & Chat Agent to a live environment.

---

## Target Platform: Railway

### Why Railway
- Simple GitHub-based deploys
- Native WebSocket support (critical for voice + chat)
- Automatic HTTPS
- Environment variable management
- Affordable ($5/mo hobby plan)

### Setup Steps

1. **Create Railway account** at https://railway.app
2. **Connect GitHub repo**
3. **Create new project** from the repo
4. **Set environment variables:**
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   DEEPGRAM_API_KEY=...
   ELEVENLABS_API_KEY=...
   ELEVENLABS_VOICE_ID=...
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   CLAUDE_MODEL=claude-sonnet-4-20250514
   SESSION_TIMEOUT_MINUTES=30
   LOG_LEVEL=INFO
   PRACTICE_ID=default
   ```
5. **Deploy** — Railway auto-detects Python and builds

### Railway Configuration

**Procfile:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Or railway.toml:**
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 5
```

---

## Twilio Configuration (Post-Deploy)

Once deployed and you have a public URL:

1. Go to Twilio Console → Phone Numbers → Your Number
2. Set Voice webhook:
   - **When a call comes in:** `https://your-app.railway.app/twilio/incoming`
   - **Method:** POST
3. Set Status callback (optional):
   - **URL:** `https://your-app.railway.app/twilio/status`
   - **Method:** POST

---

## Render (Fallback Alternative)

### Setup Steps
1. Create Render account at https://render.com
2. New → Web Service → Connect repo
3. Settings:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables (same as Railway)
5. Deploy

**Note:** Render free tier sleeps after 15 minutes of inactivity. Not ideal for voice (cold start = missed calls). Use paid tier ($7/mo) for reliable voice.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key |
| `DEEPGRAM_API_KEY` | Yes | — | Deepgram API key |
| `ELEVENLABS_API_KEY` | Yes | — | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | Yes | — | ElevenLabs voice to use |
| `TWILIO_ACCOUNT_SID` | Yes | — | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Yes | — | Twilio auth token |
| `CLAUDE_MODEL` | No | claude-sonnet-4-20250514 | Claude model ID |
| `SESSION_TIMEOUT_MINUTES` | No | 30 | Session expiry |
| `LOG_LEVEL` | No | INFO | Logging level |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (Supabase for prod) |
| `PRACTICE_ID` | No | default | Practice identifier |
| `PORT` | No | 8000 | Server port (set by platform) |

---

## Supabase Database Setup

1. Go to your Supabase dashboard: https://supabase.com/dashboard/project/airqmqvntfdvhivoenlj
2. Navigate to **Settings** → **Database**
3. Copy the **Connection string** (URI format): `postgresql://postgres:[YOUR-PASSWORD]@db.airqmqvntfdvhivoenlj.supabase.co:5432/postgres`
4. Set this as `DATABASE_URL` in Railway environment variables
5. Run migrations against Supabase: `psql $DATABASE_URL -f migrations/001_initial.sql`

**Keep-alive:** Supabase free tier pauses after 7 days of inactivity. Options:
- Background task in the FastAPI app that pings the DB every few days
- External cron service (e.g., cron-job.org) that hits our `/health` endpoint (which queries the DB)

---

## Pre-Deployment Checklist

- [ ] All environment variables documented and available
- [ ] Health endpoint works locally
- [ ] No hardcoded API keys in code
- [ ] .env file in .gitignore
- [ ] Requirements file up to date
- [ ] WebSocket endpoints tested locally
- [ ] Twilio webhook URLs ready to update
- [ ] Database migrations applied to Supabase
- [ ] Keep-alive mechanism configured for Supabase
