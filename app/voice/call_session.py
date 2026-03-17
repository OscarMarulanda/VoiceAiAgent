import asyncio
import base64
import json
import logging
import re
import time

from fastapi import WebSocket

from app.agent.core import process_message, get_last_turn_usage
from app.repositories import session_repo
from app.voice.stt import DeepgramSTT
from app.voice import tts

logger = logging.getLogger(__name__)

# Transcripts with fewer words than this get buffered (smart accumulation)
_SUBSTANTIAL_WORD_COUNT = 4

# How long to wait for more input before flushing short transcripts (seconds)
_BUFFER_TIMEOUT_S = 1.5

# If agent hasn't responded in this many seconds, play a filler phrase
_FILLER_DELAY_S = 1.5

# Overall timeout for agent processing (seconds)
_AGENT_TIMEOUT_S = 15.0

# Silence detection thresholds (ADR-035)
_SILENCE_WARNING_S = 20.0  # "Are you still there?"
_SILENCE_HANGUP_S = 30.0   # End the call

_SILENCE_WARNING_TEXT = {
    "en": "Are you still there? I'm here to help if you need anything.",
    "es": "¿Sigues ahí? Estoy aquí para ayudarte.",
}
_SILENCE_HANGUP_TEXT = {
    "en": "It seems we got disconnected. Goodbye!",
    "es": "Parece que nos desconectamos. ¡Adiós!",
}

# Farewell detection — skip agent and respond immediately.
# Must be strict to avoid false positives like "No, that's too early."
_FAREWELL_RE = re.compile(
    r"^("
    # English
    r"no[\.,]?\s*thank(s|\s*you).*"
    r"|no[\.,]?\s*i'?m good"
    r"|no[\.,]?\s*nothing else"
    r"|no[\.,]?\s*that'?s (all|it)\b"
    r"|nope[\.,]?\s*that'?s (all|it)\b"
    r"|that'?s (all|it)\b.*"
    r"|good\s*bye"
    r"|bye[\.\s]*"
    r"|have a (good|great|nice)\b.*"
    r"|see you\b.*"
    r"|nothing else"
    # Spanish
    r"|no[\.,]?\s*gracias"
    r"|no[\.,]?\s*eso es todo"
    r"|no[\.,]?\s*nada m[aá]s"
    r"|eso es todo"
    r"|nada m[aá]s"
    r"|hasta luego"
    r"|adi[oó]s"
    r"|chao"
    r"|que (te|le) vaya bien"
    # Common Deepgram mistranscriptions of Spanish farewells
    r"|no[\.,]?\s*that\s*is"
    r"|no[\.,]?\s*that'?s\s*you"
    r")[\.\!\s]*$",
    re.IGNORECASE,
)

_FAREWELL_RESPONSE = {
    "en": "Thank you for calling Sunshine Dental! Have a great day. Goodbye!",
    "es": "¡Gracias por llamar a Sunshine Dental! ¡Que tengas un excelente día! ¡Adiós!",
}

# Detect if the agent's response is a goodbye — disconnect STT to prevent interruption
_AGENT_GOODBYE_RE = re.compile(
    r"goodbye|bye|have a (good|great|nice|wonderful)\s+(day|evening|night|one)"
    r"|nos vemos|adi[oó]s|buena(s)?\s*(noches?|tardes?|d[ií]as?|suerte)"
    r"|que (te|le) vaya|hasta luego|cu[ií]date",
    re.IGNORECASE,
)

# Simple Spanish detection — presence of Spanish-specific characters or common words
_SPANISH_RE = re.compile(
    r"[ñ¿¡áéíóúü]"
    r"|(?<!\w)(?:hola|buenos?\s*d[ií]as|buenas?\s*tardes|buenas?\s*noches"
    r"|por\s*favor|porfa|gracias|quiero|necesito|puedo|cita|limpieza"
    r"|mañana|doctor[a]?|tengo|para|una?|el|la|los|las|del|con)(?!\w)",
    re.IGNORECASE,
)


class CallSession:
    """Owns the full lifecycle of one phone call (ADR-028).

    Manages state, orchestrates STT -> Agent -> TTS pipeline,
    and handles interruptions.
    """

    def __init__(self, twilio_ws: WebSocket, stream_sid: str):
        self.twilio_ws = twilio_ws
        self.stream_sid = stream_sid
        self.session_id: str | None = None
        self.is_speaking = False
        self._stt: DeepgramSTT | None = None
        # Flag to cancel in-progress TTS streaming
        self._tts_cancelled = False
        # Smart accumulation buffer for short utterances
        self._utterance_buffer: list[str] = []
        self._buffer_timer: asyncio.Task | None = None
        # Prevent concurrent agent processing
        self._processing_lock = asyncio.Lock()
        # Silence detection (ADR-035)
        self._silence_task: asyncio.Task | None = None
        self._silence_warning_sent = False
        # Call-ending flag to prevent actions after stop
        self._ended = False
        # Latency tracking (ADR-035)
        self._tts_first_chunk_t: float | None = None
        self._turn_start_t: float = 0.0
        self._agent_ms: float = 0.0
        # Accumulated metrics for DB persistence (ADR-038)
        self._metrics_turns: int = 0
        self._metrics_agent_ms_total: float = 0.0
        self._metrics_tts_first_chunk_ms_total: float = 0.0
        self._metrics_total_turn_ms_total: float = 0.0
        self._metrics_tools_used: set[str] = set()
        self._metrics_appointment_booked: bool = False
        self._metrics_outcome: str = "completed"  # completed, abandoned, error
        # Token usage tracking
        self._metrics_input_tokens: int = 0
        self._metrics_output_tokens: int = 0
        # Language detection
        self._lang: str = "en"
        self._lang_detected: bool = False

    async def start(self, caller_number: str | None = None) -> None:
        """Initialize the call: create agent session, connect STT, play greeting."""
        # Create agent session in DB
        session = await session_repo.create_session(
            channel="voice",
            caller_number=caller_number,
        )
        self.session_id = session["id"]
        logger.info("Call session started — session_id=%s", self.session_id)

        # Connect Deepgram STT
        self._stt = DeepgramSTT(
            on_transcript=self._on_transcript,
            on_speech_started=self._on_speech_started,
            on_connection_lost=self._on_stt_connection_lost,
        )
        await self._stt.connect()

        # Play pre-generated greeting (ADR-027)
        greeting = tts.get_cached_greeting()
        if greeting:
            await self._send_audio_to_twilio(greeting)
        else:
            # Fallback: generate live if cache missed
            logger.warning("Greeting not cached — generating live")
            async for chunk in tts.synthesize_stream(tts.GREETING_TEXT):
                await self._send_audio_to_twilio(chunk)

    async def handle_audio(self, payload: str) -> None:
        """Forward base64-encoded Twilio audio to Deepgram."""
        if self._stt is not None and not self._ended:
            try:
                audio_bytes = base64.b64decode(payload)
                await self._stt.send_audio(audio_bytes)
            except Exception:
                pass  # STT already closed (call ending)

    async def stop(self) -> None:
        """Clean up: close STT, cancel timers, persist metrics, end agent session."""
        self._ended = True

        if self._silence_task is not None:
            self._silence_task.cancel()
            self._silence_task = None

        if self._buffer_timer is not None:
            self._buffer_timer.cancel()
            self._buffer_timer = None

        if self._stt is not None:
            await self._stt.close()
            self._stt = None

        if self.session_id:
            # Read session context to extract tools_used + appointment_booked (ADR-038)
            try:
                ctx = await session_repo.get_context(self.session_id)
                tool_log = ctx.get("tool_log", [])
                self._metrics_tools_used = {entry["tool"] for entry in tool_log if "tool" in entry}
                notepad = ctx.get("notepad", {})
                self._metrics_appointment_booked = bool(notepad.get("last_booking"))
            except Exception:
                logger.exception("Failed to read context for metrics — session %s", self.session_id)

            # Persist accumulated metrics (ADR-038)
            try:
                await session_repo.update_metrics(self.session_id, self._build_metrics())
            except Exception:
                logger.exception("Failed to persist metrics for session %s", self.session_id)

            try:
                await session_repo.end_session(self.session_id)
            except Exception:
                logger.exception("Failed to end session %s", self.session_id)

        logger.info("Call session ended — session_id=%s", self.session_id)

    def _build_metrics(self) -> dict:
        """Build the metrics dict to persist to DB."""
        turns = self._metrics_turns
        metrics: dict = {
            "total_turns": turns,
            "tools_used": sorted(self._metrics_tools_used),
            "appointment_booked": self._metrics_appointment_booked,
            "outcome": self._metrics_outcome,
            "input_tokens": self._metrics_input_tokens,
            "output_tokens": self._metrics_output_tokens,
            "total_tokens": self._metrics_input_tokens + self._metrics_output_tokens,
        }
        if turns > 0:
            metrics["avg_agent_ms"] = round(self._metrics_agent_ms_total / turns, 0)
            metrics["avg_tts_first_chunk_ms"] = round(self._metrics_tts_first_chunk_ms_total / turns, 0)
            metrics["avg_total_turn_ms"] = round(self._metrics_total_turn_ms_total / turns, 0)
        return metrics

    # ------------------------------------------------------------------
    # Smart accumulation
    # ------------------------------------------------------------------

    async def _on_transcript(self, text: str) -> None:
        """Called when Deepgram produces a final utterance.

        Short transcripts (< 4 words) are buffered with a 1.5s timeout
        so digit-by-digit dictation gets accumulated into one message.
        Substantial transcripts flush the buffer immediately.
        """
        if self._ended:
            return

        logger.info("Transcript received: %s", text)

        # Reset silence detection — patient is still here
        self._reset_silence_timer()
        self._silence_warning_sent = False

        self._utterance_buffer.append(text)

        # Cancel any existing timer
        if self._buffer_timer is not None:
            self._buffer_timer.cancel()
            self._buffer_timer = None

        # Substantial transcript → flush immediately
        word_count = len(text.split())
        if word_count >= _SUBSTANTIAL_WORD_COUNT:
            await self._flush_buffer()
        else:
            # Short transcript → wait for more
            self._buffer_timer = asyncio.create_task(self._buffer_timeout())

    async def _buffer_timeout(self) -> None:
        """Fire after silence — flush whatever is in the buffer."""
        try:
            await asyncio.sleep(_BUFFER_TIMEOUT_S)
        except asyncio.CancelledError:
            return  # Timer cancelled because new transcript arrived

        # Clear self-reference so _on_transcript can't cancel us mid-processing
        self._buffer_timer = None

        try:
            await self._flush_buffer()
        except Exception:
            logger.exception("Error in buffer timeout")

    async def _flush_buffer(self) -> None:
        """Join buffered transcripts and send to agent (or handle farewell)."""
        if not self._utterance_buffer:
            return

        if self._buffer_timer is not None:
            self._buffer_timer.cancel()
            self._buffer_timer = None

        full_text = " ".join(self._utterance_buffer).strip()
        self._utterance_buffer.clear()

        if not full_text:
            return

        # Detect language from first substantial transcript
        if not self._lang_detected:
            self._lang_detected = True
            if _SPANISH_RE.search(full_text):
                self._lang = "es"
                logger.info("Language detected: Spanish")
                if self.session_id:
                    asyncio.create_task(session_repo.update_language(self.session_id, "es"))

        # Farewell detection — respond instantly without hitting the agent
        if _FAREWELL_RE.search(full_text):
            logger.info("Farewell detected: %s", full_text)
            # Disconnect STT so VAD can't trigger interruption during goodbye
            if self._stt is not None:
                await self._stt.close()
                self._stt = None
            async with self._processing_lock:
                await self._speak(_FAREWELL_RESPONSE[self._lang], restart_silence_timer=False)
            await self._end_call()
            return

        async with self._processing_lock:
            try:
                await self._process_and_speak(full_text)
            except Exception:
                logger.exception("Error processing utterance: %s", full_text)
                # Play error clip so patient doesn't hear silence (ADR-035)
                error_clip = tts.get_cached_error_clip()
                if error_clip:
                    await self._send_audio_to_twilio(error_clip)

    # ------------------------------------------------------------------
    # Agent processing + TTS
    # ------------------------------------------------------------------

    async def _process_and_speak(self, text: str) -> None:
        """Send text to Agent Core, then stream TTS response to Twilio.

        Launches a fire-and-forget filler task that plays a phrase if
        the agent takes longer than _FILLER_DELAY_S to respond.
        """
        turn_start = time.monotonic()
        logger.info("Patient said: %s", text)

        # Cancel silence timer — we're processing now
        if self._silence_task is not None:
            self._silence_task.cancel()
            self._silence_task = None

        # Interrupt any in-progress TTS
        if self.is_speaking:
            await self._handle_interruption()

        # Fire-and-forget: play a filler if agent is slow
        filler_task = asyncio.create_task(self._play_filler_after_delay())

        agent_start = time.monotonic()
        try:
            response_text = await asyncio.wait_for(
                process_message(self.session_id, text),
                timeout=_AGENT_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.warning("Agent timed out for session %s", self.session_id)
            response_text = (
                "I'm sorry, I'm having a little trouble right now. "
                "Could you try again?"
            )
        except Exception:
            logger.exception("Agent error for session %s", self.session_id)
            response_text = (
                "I'm sorry, I'm having a little trouble right now. "
                "Could you try again?"
            )
        finally:
            filler_task.cancel()

        agent_ms = (time.monotonic() - agent_start) * 1000

        # Accumulate token usage
        usage = get_last_turn_usage()
        self._metrics_input_tokens += usage["input_tokens"]
        self._metrics_output_tokens += usage["output_tokens"]

        logger.info("Agent response: %s", response_text)

        # If agent is saying goodbye, disconnect STT to prevent interruption
        is_goodbye = bool(_AGENT_GOODBYE_RE.search(response_text))
        if is_goodbye:
            logger.info("Agent goodbye detected — disconnecting STT")
            if self._stt is not None:
                await self._stt.close()
                self._stt = None

        # Track TTS first-chunk latency (ADR-035)
        self._tts_first_chunk_t = time.monotonic()
        self._turn_start_t = turn_start
        self._agent_ms = agent_ms
        await self._speak(response_text, restart_silence_timer=not is_goodbye)

        if is_goodbye:
            await self._end_call()

    async def _play_filler_after_delay(self) -> None:
        """Wait _FILLER_DELAY_S, then play a cached filler phrase.

        Designed to be cancelled when the agent responds before the delay.
        """
        try:
            await asyncio.sleep(_FILLER_DELAY_S)
            filler = tts.get_random_filler(lang=self._lang)
            if filler:
                logger.info("Playing filler while agent is thinking")
                await self._send_audio_to_twilio(filler)
        except asyncio.CancelledError:
            pass  # Agent responded before filler was needed
        except Exception:
            logger.warning("Filler playback failed", exc_info=True)

    async def _speak(self, text: str, restart_silence_timer: bool = True) -> None:
        """Stream TTS for the given text to Twilio."""
        if self._ended:
            return

        self.is_speaking = True
        self._tts_cancelled = False

        try:
            async for chunk in tts.synthesize_stream(text, lang=self._lang):
                if self._tts_cancelled:
                    break
                await self._send_audio_to_twilio(chunk)
        except Exception:
            logger.exception("TTS error for session %s — playing cached error clip", self.session_id)
            # Fallback: play pre-cached error clip (ADR-035)
            error_clip = tts.get_cached_error_clip()
            if error_clip:
                await self._send_audio_to_twilio(error_clip)
        finally:
            self.is_speaking = False

        # Start silence timer — it's now the patient's turn (ADR-035)
        # Disabled for silence monitor speech to avoid restarting the monitor
        if restart_silence_timer:
            self._start_silence_timer()

    # ------------------------------------------------------------------
    # Interruption handling (ADR-026)
    # ------------------------------------------------------------------

    async def _on_speech_started(self) -> None:
        """Called when Deepgram detects the patient started speaking (VAD)."""
        if self.is_speaking:
            await self._handle_interruption()

    async def _handle_interruption(self) -> None:
        """Stop TTS playback when patient speaks (ADR-026)."""
        logger.info("Interruption — clearing Twilio audio")
        self._tts_cancelled = True
        self.is_speaking = False

        # Tell Twilio to flush its audio queue
        clear_msg = json.dumps({
            "event": "clear",
            "streamSid": self.stream_sid,
        })
        await self.twilio_ws.send_text(clear_msg)

    # ------------------------------------------------------------------
    # Twilio audio output
    # ------------------------------------------------------------------

    async def _send_audio_to_twilio(self, audio_bytes: bytes) -> None:
        """Base64-encode audio and send as Twilio media event."""
        # Log + accumulate latency on first TTS chunk of a turn (ADR-035, ADR-038)
        if self._tts_first_chunk_t is not None:
            now = time.monotonic()
            tts_first_chunk_ms = (now - self._tts_first_chunk_t) * 1000
            total_turn_ms = (now - self._turn_start_t) * 1000
            logger.info(
                "Latency — agent=%.0fms tts_first_chunk=%.0fms total_turn=%.0fms | session=%s",
                self._agent_ms, tts_first_chunk_ms, total_turn_ms, self.session_id,
            )
            # Accumulate for session-level metrics (ADR-038)
            self._metrics_turns += 1
            self._metrics_agent_ms_total += self._agent_ms
            self._metrics_tts_first_chunk_ms_total += tts_first_chunk_ms
            self._metrics_total_turn_ms_total += total_turn_ms
            self._tts_first_chunk_t = None  # Only log once per turn

        payload = base64.b64encode(audio_bytes).decode("ascii")
        msg = json.dumps({
            "event": "media",
            "streamSid": self.stream_sid,
            "media": {"payload": payload},
        })
        await self.twilio_ws.send_text(msg)

    # ------------------------------------------------------------------
    # Silence detection (ADR-035)
    # ------------------------------------------------------------------

    def _start_silence_timer(self) -> None:
        """Start the silence detection timer (called after agent finishes speaking)."""
        if self._ended:
            return
        if self._silence_task is not None:
            self._silence_task.cancel()
        self._silence_task = asyncio.create_task(self._silence_monitor())

    def _reset_silence_timer(self) -> None:
        """Reset the silence timer (called on transcript received)."""
        if self._silence_task is not None:
            self._silence_task.cancel()
            self._silence_task = None
        self._start_silence_timer()

    async def _silence_monitor(self) -> None:
        """Monitor for patient silence and act at thresholds."""
        try:
            # Wait for warning threshold
            await asyncio.sleep(_SILENCE_WARNING_S)

            if self._ended or self.is_speaking:
                return

            logger.info("Silence detected (%.0fs) — sending warning | session=%s",
                        _SILENCE_WARNING_S, self.session_id)
            self._silence_warning_sent = True
            async with self._processing_lock:
                await self._speak(_SILENCE_WARNING_TEXT[self._lang], restart_silence_timer=False)

            # Wait for hangup threshold (remaining time after warning)
            await asyncio.sleep(_SILENCE_HANGUP_S - _SILENCE_WARNING_S)

            if self._ended:
                return

            logger.info("Silence detected (%.0fs) — ending call | session=%s",
                        _SILENCE_HANGUP_S, self.session_id)
            self._metrics_outcome = "abandoned"
            async with self._processing_lock:
                await self._speak(_SILENCE_HANGUP_TEXT[self._lang], restart_silence_timer=False)

            # End the call
            await self._end_call()

        except asyncio.CancelledError:
            pass  # Timer reset or call ended
        except Exception:
            logger.exception("Error in silence monitor")

    # ------------------------------------------------------------------
    # Deepgram connection drop (ADR-035)
    # ------------------------------------------------------------------

    async def _on_stt_connection_lost(self) -> None:
        """Called when Deepgram WebSocket drops unexpectedly."""
        if self._ended:
            return

        logger.error("STT connection lost — playing error clip and ending call | session=%s",
                      self.session_id)

        error_clip = tts.get_cached_error_clip()
        if error_clip:
            await self._send_audio_to_twilio(error_clip)

        await self._end_call()

    # ------------------------------------------------------------------
    # Graceful call termination
    # ------------------------------------------------------------------

    async def _end_call(self) -> None:
        """Gracefully end the Twilio media stream.

        Waits a few seconds after the last audio to let Twilio finish
        playing buffered audio before closing the connection.
        """
        if self._ended:
            return
        self._ended = True

        # Give Twilio time to play the goodbye audio before closing
        await asyncio.sleep(4)

        try:
            await self.twilio_ws.close()
        except Exception:
            pass  # Already closed or disconnected — fine
