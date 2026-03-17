# Costs

Estimated costs for running the AI Voice & Chat Agent. All prices are as of early 2025 and may change.

---

## Summary Table

| Service | Cost Type | Estimated Monthly (Demo) | Notes |
|---------|-----------|--------------------------|-------|
| Claude API (Anthropic) | Per token | $5 – $15 | Depends on usage volume |
| Deepgram STT | Per minute | $2 – $5 | Pay-as-you-go |
| Deepgram TTS | Per character | $0 | Covered by $200 free credit |
| Twilio Phone Number | Monthly | $1.15 | One US number |
| Twilio Voice | Per minute | $2 – $5 | Inbound calls |
| Railway/Render | Monthly | $5 – $7 | Basic plan |
| Supabase (PostgreSQL) | Monthly | $0 | Free tier (500 MB) |
| SendGrid (Email) | Monthly | $0 | Free tier (100/day) |
| **Total (Demo)** | | **$13 – $32/mo** | Light demo usage |

---

## Detailed Breakdown

### 1. Claude API (Anthropic)

**Model: Claude Sonnet (primary choice for voice — balances speed + quality)**

| Metric | Price |
|--------|-------|
| Input tokens | $3.00 / 1M tokens |
| Output tokens | $15.00 / 1M tokens |

**Estimated per conversation (voice or chat):**
- System prompt: ~800 tokens (input, sent every turn)
- Average conversation: 10 turns
- Per turn: ~200 input tokens (user + history) + ~150 output tokens (response)
- Tool calls add: ~100 input + ~200 output tokens per tool round-trip
- **Total per conversation: ~10,000 input + ~3,000 output tokens**
- **Cost per conversation: ~$0.03 + $0.045 = ~$0.075**

**Monthly estimate (demo: ~100 conversations):** ~$7.50

**If using Claude Haiku instead (for simple queries):**

| Metric | Price |
|--------|-------|
| Input tokens | $0.25 / 1M tokens |
| Output tokens | $1.25 / 1M tokens |

Could reduce LLM costs by ~90% for simple FAQ queries.

---

### 2. Deepgram Speech-to-Text

**Model: Nova-2 (Pay-as-you-go)**

| Metric | Price |
|--------|-------|
| Real-time streaming STT | $0.0043 / minute |

**Estimated per voice call:**
- Average call duration: 3-5 minutes
- **Cost per call: ~$0.013 – $0.022**

**Monthly estimate (demo: ~50 voice calls):** ~$1.00

**Free tier:** Deepgram offers $200 in free credits for new accounts — enough for the entire demo period.

---

### 3. Deepgram Aura Text-to-Speech (ADR-039)

**Replaced ElevenLabs** after the free tier (10,000 chars/month) was exhausted during development. Deepgram was already in the stack for STT with $200 free credit.

**Pricing:**

| Metric | Price |
|--------|-------|
| Per character | $0.015 / 1K characters |

**Estimated per voice call:**
- Average AI response: ~100 characters per turn
- Average turns per call: 5-8 AI responses
- **Characters per call: ~500 – 800**
- **Cost per call: ~$0.008 – $0.012**

**Monthly estimate (demo: ~50 voice calls):**
- ~25,000 – 40,000 characters
- **Cost: ~$0.38 – $0.60** (covered by $200 free credit)

**Note:** With $200 Deepgram credit, TTS costs are effectively $0 for the entire demo period (~13 million characters).

---

### 4. Twilio

**Phone number:**

| Item | Price |
|------|-------|
| US local phone number | $1.15/month |
| US toll-free number | $2.15/month |

**Voice (inbound calls):**

| Item | Price |
|------|-------|
| Inbound call (per minute) | $0.0085/min |
| Media Streams (per minute) | Included with voice |

**Estimated per call:**
- Average duration: 3-5 minutes
- **Cost per call: ~$0.025 – $0.043**

**Monthly estimate (demo):**
- Phone number: $1.15
- 50 calls × 4 min avg: ~$1.70
- **Total Twilio: ~$2.85/mo**

**Free trial:** Twilio provides trial credit (~$15) for new accounts. We upgraded to paid ($20 loaded) because trial accounts can only receive calls from verified numbers.

---

### 5. SendGrid (Email Notifications — ADR-037)

**Plan: Free tier**

| Item | Price |
|------|-------|
| Emails/day | 100 (free) |
| Monthly cost | $0 |

**Estimated usage (demo):**
- Each booking/cancellation/reschedule sends 2 emails (patient + provider)
- 50 bookings + 10 cancellations + 5 reschedules = ~130 emails/month
- Well within 100/day limit

**Why not SMS:** International SMS from US Twilio number to Colombia costs ~$0.0375/message. Email is free and works globally.

---

### 6. Hosting (Railway)

| Plan | Price | Includes |
|------|-------|----------|
| Hobby | $5/mo | 512MB RAM, 1 vCPU, 5GB disk |
| Pro | $20/mo | More resources |

**For demo:** Hobby plan ($5/mo) is sufficient. May need to upgrade if WebSocket connections are heavy.

**Render alternative:** Free tier available (spins down after inactivity, cold start ~30s — not ideal for voice).

---

### 6. Database (Supabase PostgreSQL)

**Plan: Free tier**

| Item | Price |
|------|-------|
| Storage | 500 MB (free) |
| Database | Shared instance |
| Bandwidth | 2 GB/mo |
| Pausing | After 7 days inactivity |

**Current usage on existing account:** ~24 MB of 500 MB. Our project adds ~1-2 MB.

**Cost:** $0/mo — fully covered by free tier.

**Keep-alive note:** Free tier pauses after 7 days of inactivity. We implement a scheduled ping (cron job or in-app background task) to prevent this. Zero cost.

---

## Cost Scenarios

### Scenario A: Development Phase
Very light usage — testing and building.

| Service | Cost |
|---------|------|
| Claude API | ~$2 (testing) |
| Deepgram | $0 (free credits) |
| Deepgram TTS | $0 (free credits) |
| Twilio | $0 (trial credits) |
| SendGrid | $0 (free tier) |
| Hosting | $0 (local development) |
| Database | $0 (local PostgreSQL) |
| **Total** | **~$2** |

### Scenario B: Demo Phase (Light)
Live demo available, ~5-10 calls/chats per day for a week.

| Service | Cost |
|---------|------|
| Claude API | ~$5 |
| Deepgram | ~$1 (or free credits) |
| Deepgram TTS | $0 (free credits) |
| Twilio | ~$3 |
| SendGrid | $0 (free tier) |
| Hosting | $5 (Railway Hobby) |
| Database | $0 (Supabase free tier) |
| **Total** | **~$14/mo** |

### Scenario C: Active Demo (Heavy)
Shared widely, 20-30 interactions/day.

| Service | Cost |
|---------|------|
| Claude API | ~$15 |
| Deepgram | ~$5 |
| Deepgram TTS | $0 (free credits) |
| Twilio | ~$5 |
| SendGrid | $0 (free tier) |
| Hosting | $5 (Railway Hobby) |
| Database | $0 (Supabase free tier) |
| **Total** | **~$30/mo** |

---

## Cost Optimization Strategies

1. **Use Claude Haiku for simple queries** — FAQ responses (hours, insurance, location) don't need Sonnet. Route simple queries to Haiku ($0.25/1M input) and save Sonnet for complex interactions (booking, rescheduling).

2. **Cache common TTS responses** — Pre-generate audio for the greeting, common phrases, and error messages. Saves ElevenLabs characters.

3. **Set usage limits** — Cap daily conversations to prevent unexpected bills during demo.

4. **Use free tiers during development** — Deepgram free credits, ElevenLabs free tier, Twilio trial — develop without spending.

5. **Monitor and alert** — Set up billing alerts on all services.

---

## API Keys Required

| Service | Environment Variable | Where to Get |
|---------|---------------------|--------------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| Deepgram | `DEEPGRAM_API_KEY` | https://console.deepgram.com |
| Deepgram (STT + TTS) | `DEEPGRAM_API_KEY` | https://console.deepgram.com |
| Twilio (SID) | `TWILIO_ACCOUNT_SID` | https://console.twilio.com |
| Twilio (Token) | `TWILIO_AUTH_TOKEN` | https://console.twilio.com |
| SendGrid | `SENDGRID_API_KEY` | https://app.sendgrid.com/settings/api_keys |
| Supabase (DB) | `DATABASE_URL` | https://supabase.com/dashboard → Project → Settings → Database |

---

## Free Tier / Trial Summary

| Service | Free Offering | Enough For |
|---------|---------------|------------|
| Deepgram | $200 credit | ~46,000 minutes of STT |
| Deepgram TTS | $200 credit (~13M chars) | Entire project and more |
| Twilio | ~$15 trial credit | ~350 minutes of calls + number |
| Anthropic | Varies by account | Check console |
| SendGrid | 100 emails/day | Entire project and more |
| Supabase | 500 MB free forever | Entire project and more |
| Railway | $5 trial credit | 1 month hobby |

**Bottom line:** You can build and lightly demo this project for nearly free using trial credits, then spend ~$20-50/mo for active demo usage.

---

## Actual Spending (Running Total)

| Date | Service | Amount | Notes |
|------|---------|--------|-------|
| 2026-03-11 | Twilio | $20.00 | Upgraded from trial to paid account |
| | **Total spent** | **$20.00** | |

All other services currently on free tiers:
- Deepgram: Free $200 credit (covers both STT and TTS — ADR-039)
- ElevenLabs: No longer used (free tier exhausted, replaced by Deepgram Aura — ADR-039)
- ngrok: Free tier (domain: arie-euphotic-nonpictorially.ngrok-free.dev)
- Supabase: Free tier
