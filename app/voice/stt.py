import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.listen.v1.types import (
    ListenV1Results,
    ListenV1SpeechStarted,
    ListenV1UtteranceEnd,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Type for the transcript callback: async fn(transcript: str) -> None
TranscriptCallback = Callable[[str], Coroutine[Any, Any, None]]

# Type for the speech-started callback: async fn() -> None
SpeechStartedCallback = Callable[[], Coroutine[Any, Any, None]]


# Type for the connection-closed callback: async fn() -> None (ADR-035)
ConnectionClosedCallback = Callable[[], Coroutine[Any, Any, None]]


class DeepgramSTT:
    """Stateless-ish wrapper around Deepgram streaming STT.

    One instance per active call. Accumulates is_final segments and fires
    the on_transcript callback when speech_final=True (end of utterance).
    """

    def __init__(
        self,
        on_transcript: TranscriptCallback,
        on_speech_started: SpeechStartedCallback | None = None,
        on_connection_lost: ConnectionClosedCallback | None = None,
    ):
        self._on_transcript = on_transcript
        self._on_speech_started = on_speech_started
        self._on_connection_lost = on_connection_lost
        self._connection = None
        self._listen_task: asyncio.Task | None = None
        self._transcript_buffer: list[str] = []
        self._closed = False

    async def connect(self) -> None:
        """Open a streaming WebSocket connection to Deepgram."""
        client = AsyncDeepgramClient(api_key=settings.deepgram_api_key)

        self._ctx = client.listen.v1.connect(
            model="nova-3",
            encoding="mulaw",
            sample_rate="8000",
            interim_results="true",
            utterance_end_ms="1000",
            endpointing="300",
            punctuate="true",
            vad_events="true",
            language="multi",
        )
        self._connection = await self._ctx.__aenter__()

        self._connection.on(EventType.MESSAGE, self._on_message)
        self._connection.on(EventType.ERROR, self._on_error)

        # start_listening() blocks until the WS closes — run as background task
        self._listen_task = asyncio.create_task(self._connection.start_listening())
        self._listen_task.add_done_callback(self._on_listen_done)

        logger.info("Deepgram STT connected")

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Forward raw mulaw audio bytes to Deepgram."""
        if self._connection is not None:
            await self._connection.send_media(audio_bytes)

    def _on_listen_done(self, task: asyncio.Task) -> None:
        """Called when the Deepgram listen task finishes (ADR-035).

        If it ended unexpectedly (not via our close()), notify CallSession.
        """
        if self._closed:
            return  # We closed it intentionally — nothing to do

        exc = task.exception() if not task.cancelled() else None
        logger.error("Deepgram connection lost unexpectedly: %s", exc)

        if self._on_connection_lost is not None:
            asyncio.create_task(self._on_connection_lost())

    async def close(self) -> None:
        """Close the Deepgram connection."""
        self._closed = True
        if self._connection is not None:
            try:
                await self._connection.send_close_stream()
            except Exception:
                pass

        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except (asyncio.CancelledError, Exception):
                pass

        if self._ctx is not None:
            try:
                await self._ctx.__aexit__(None, None, None)
            except Exception:
                pass

        self._connection = None
        self._listen_task = None
        logger.info("Deepgram STT disconnected")

    async def _on_message(self, message: Any) -> None:
        """Handle incoming messages from Deepgram."""
        if isinstance(message, ListenV1Results):
            transcript = ""
            if message.channel and message.channel.alternatives:
                transcript = message.channel.alternatives[0].transcript

            if not transcript:
                return

            if message.is_final:
                self._transcript_buffer.append(transcript)

                if message.speech_final:
                    full_text = " ".join(self._transcript_buffer).strip()
                    self._transcript_buffer.clear()
                    if full_text:
                        logger.info("Transcript: %s", full_text)
                        await self._on_transcript(full_text)

        elif isinstance(message, ListenV1UtteranceEnd):
            # Backup signal — flush buffer if speech_final didn't fire
            if self._transcript_buffer:
                full_text = " ".join(self._transcript_buffer).strip()
                self._transcript_buffer.clear()
                if full_text:
                    logger.info("Transcript (utterance end): %s", full_text)
                    await self._on_transcript(full_text)

        elif isinstance(message, ListenV1SpeechStarted):
            if self._on_speech_started is not None:
                await self._on_speech_started()

    async def _on_error(self, error: Any) -> None:
        """Handle Deepgram errors."""
        logger.error("Deepgram STT error: %s", error)
