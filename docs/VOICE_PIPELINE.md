# Voice Pipeline

Detailed documentation of the voice processing pipeline — from phone ring to AI response.

---

## Overview

```
Patient's Phone
      │
      ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Twilio   │────►│  Deepgram    │────►│  Claude API  │────►│  ElevenLabs  │
│  (call)   │◄────│  (STT)       │     │  (agent)     │     │  (TTS)       │
└──────────┘     └──────────────┘     └──────────────┘     └──────────────┘
   mulaw            text                  text                 audio
   8kHz             transcript            response             stream
```

## Step-by-Step Flow

### Phase 1: Call Setup

1. **Patient dials the Twilio phone number**
2. Twilio sends an HTTP POST to our webhook: `POST /twilio/incoming`
3. Our server responds with TwiML:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
     <Connect>
       <Stream url="wss://our-server.com/twilio/media-stream">
         <Parameter name="session_id" value="uuid-here" />
       </Stream>
     </Connect>
   </Response>
   ```
4. Twilio opens a WebSocket connection to our `/twilio/media-stream` endpoint
5. We create a new session and initialize:
   - Deepgram streaming STT connection
   - Conversation history (empty)
   - Play a pre-generated greeting: "Hello! Thank you for calling Sunshine Dental. How can I help you today?"

### Phase 2: Listening (Patient Speaks)

6. Twilio sends audio chunks via WebSocket as JSON messages:
   ```json
   {
     "event": "media",
     "media": {
       "payload": "base64-encoded-mulaw-audio",
       "timestamp": "1234",
       "chunk": "1"
     }
   }
   ```
7. We decode the base64 audio and forward it to Deepgram's streaming WebSocket
8. Deepgram processes audio in real-time and sends back transcription events:
   - **Interim results** — Partial transcription as speech is happening (useful for UI, not used for voice)
   - **Final results** — Complete transcription of an utterance after endpointing

### Phase 3: Transcript Accumulation (Smart Buffering — ADR-030)

9. On receiving a **final transcription** from Deepgram:
   - If the transcript is **substantial** (4+ words): flush buffer immediately — send to agent
   - If the transcript is **short** (<4 words, e.g., a single digit or "yes"): add to buffer, start/reset a 1.5-second timer
   - When timer fires (patient went quiet): join all buffered text into one message, send to agent
   - This prevents digit-by-digit dictation from triggering individual agent responses

### Phase 3b: Farewell Detection (ADR-032)

10. Before sending to the agent, check if the text matches a farewell pattern ("no thank you", "bye", "that's all", etc.)
    - If farewell: skip agent entirely, play canned farewell TTS, call ends
    - If not farewell: proceed to agent processing

### Phase 4: Processing (AI Thinks — ADR-031)

11. Acquire the processing lock (ADR-034) — only one transcript processed at a time per call
12. Launch a fire-and-forget filler task: if agent takes >1.5s, play a pre-cached phrase ("Let me check on that...")
13. Send text to Agent Core: `process_message(session_id, transcript)` (with 15s timeout)
    - Agent Core builds Claude API request with voice-specific system prompt (ADR-029)
    - Claude may call tools (check_availability, book_appointment, etc.)
    - Past time slots are filtered out for today (ADR-033)
14. When agent responds, cancel the filler task

### Phase 5: Responding (AI Speaks)

15. Agent Core returns the text response (1-2 sentences for voice — ADR-029)
16. We send the text to ElevenLabs TTS API (streaming endpoint)
17. ElevenLabs streams back audio chunks in ulaw_8000 format (ADR-024 — no conversion needed)
18. We forward each chunk to Twilio via the Media Stream WebSocket:
    ```json
    {
      "event": "media",
      "streamSid": "stream-sid-here",
      "media": {
        "payload": "base64-encoded-mulaw-audio"
      }
    }
    ```
19. Twilio plays the audio to the patient
20. Release the processing lock, loop back to Phase 2 — listen for next utterance

### Phase 5: Call End

19. Patient hangs up OR agent says goodbye
20. Twilio sends a `stop` event on the WebSocket
21. We close Deepgram connection
22. We mark the session as ended
23. Conversation is available in admin dashboard

---

## Audio Format Details

| Stage | Format | Sample Rate | Encoding |
|-------|--------|-------------|----------|
| Twilio → Us | mulaw | 8kHz | base64 |
| Us → Deepgram | PCM (linear16) or mulaw | 8kHz | raw bytes |
| ElevenLabs → Us | mulaw (requested) | 8kHz | raw bytes |
| Us → Twilio | mulaw | 8kHz | base64 |

**Decision (ADR-024):** We request `ulaw_8000` directly from ElevenLabs — no conversion needed. Audio goes straight from ElevenLabs → base64 encode → Twilio. Fallback: convert from PCM 22050Hz → mulaw 8kHz using `audioop-lte` if quality is poor.

---

## Latency Optimization Strategies

### 1. Stream TTS Chunks Directly (ADR-025)
- **Decided approach:** Forward each ElevenLabs audio chunk to Twilio as it arrives
- ~500ms to first audio — lowest latency option
- No buffering logic needed — straightforward async chunk forwarding
- Sentence-level streaming deferred as future optimization (Phase 6 if needed)

### 2. Pre-Generated Audio (ADR-027, ADR-031)
- **Greeting message:** Pre-generate at app startup, cache as bytes in memory, play instantly on call connect
- **Filler phrases (ADR-031):** 4 phrases pre-generated at startup, played randomly when agent takes >1.5s
- Error messages: Pre-generate for instant playback (future)

### 3. Interruption Handling (ADR-026)
- **Decided approach:** Stop TTS immediately when Deepgram detects patient speech (VAD event)
- Send Twilio `clear` event to flush queued audio
- Track `is_speaking` state (boolean) in call session
- Deepgram endpointing filters out very short sounds (coughs, "um")

### 4. Smart Transcript Accumulation (ADR-030)
- Short utterances (<4 words) are buffered with a 1.5s timer
- Substantial utterances (4+ words) flush immediately — no added latency for normal conversation
- Prevents digit-by-digit dictation from triggering individual agent responses

### 5. Farewell Detection (ADR-032)
- Regex-based detection of common farewells ("no thank you", "bye", "that's all")
- Matching farewells skip agent entirely — instant canned TTS response
- Strict regex to avoid false positives (e.g., "No. That's too early" does NOT match)

---

## Twilio Media Streams Protocol

### Events We Receive:
- `connected` — Stream connected, contains `streamSid`
- `start` — Stream started, contains call metadata
- `media` — Audio chunk from caller
- `stop` — Stream stopped (call ended or stream closed)

### Events We Send:
- `media` — Audio chunk to play to caller
- `clear` — Clear any queued audio (for interruption handling)

### Mark Events (Optional):
- We can send `mark` events to know when audio finishes playing
- Useful for knowing when the AI is done speaking

---

## Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| Deepgram connection drops | WebSocket close event | Reconnect, notify user of brief interruption |
| Deepgram returns empty/low-confidence | Check confidence score | Ask patient to repeat |
| Claude API timeout | asyncio.wait_for with 15s timeout | Filler plays at 1.5s (ADR-031), graceful error message at 15s |
| Claude API error | Exception handling | Apologize, offer to try again |
| ElevenLabs timeout | asyncio.wait_for with 3s timeout | Fall back to Twilio `<Say>` (robotic but functional) |
| ElevenLabs error | Exception handling | Same fallback |
| Twilio WebSocket drops | Connection close event | Session ends, log for dashboard |

---

## Language Detection for Bilingual Support

**Approach:** Let Deepgram and Claude handle it naturally.

1. **Deepgram**: Configure for multi-language (en + es). It detects the language automatically.
2. **Claude**: System prompt instructs: "If the patient speaks in Spanish, respond in Spanish. If English, respond in English."
3. **ElevenLabs**: Use a multilingual voice model that handles both English and Spanish.

No explicit language detection code needed — the AI stack handles it end-to-end.
