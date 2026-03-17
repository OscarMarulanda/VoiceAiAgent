"""Text-to-Speech via Deepgram Aura (replaces ElevenLabs — ADR-024, ADR-027, ADR-031, ADR-035).

Provides streaming TTS in mulaw/8000 format for Twilio, plus pre-generated
audio caches for greeting, filler phrases, and error clips.
"""

import logging
import random
from collections.abc import AsyncIterator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Deepgram Aura voice model — handles English and Spanish
MODEL = "aura-asteria-en"

# Base URL for Deepgram TTS
_BASE_URL = "https://api.deepgram.com/v1/speak"

# Query params: mulaw encoding, 8kHz sample rate, no WAV container (raw bytes)
_PARAMS = {"model": MODEL, "encoding": "mulaw", "sample_rate": "8000", "container": "none"}

# Greeting text for pre-generation (ADR-027)
GREETING_TEXT = (
    "Hello! Thank you for calling Sunshine Dental. "
    "How can I help you today?"
)

# Filler phrases — played while agent is thinking (pre-cached at startup)
FILLER_PHRASES = [
    "Let me check on that for you.",
    "One moment, please.",
    "Sure, let me look that up.",
    "Let me see what we have available.",
]

# Error message — pre-cached for TTS/STT failure fallback (ADR-035)
ERROR_TEXT = (
    "We're experiencing technical difficulties. "
    "Please try calling back in a moment. Goodbye!"
)

# Module-level caches
_greeting_audio: bytes | None = None
_filler_audio: list[bytes] = []
_error_audio: bytes | None = None


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": "application/json",
    }


async def synthesize_stream(text: str) -> AsyncIterator[bytes]:
    """Stream TTS audio chunks in raw mulaw/8000 format.

    Yields raw mulaw bytes — caller is responsible for base64-encoding
    and sending to Twilio.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        async with client.stream(
            "POST",
            _BASE_URL,
            params=_PARAMS,
            headers=_headers(),
            json={"text": text},
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                yield chunk


async def _synthesize_full(text: str) -> bytes:
    """Generate complete audio for a text (non-streaming, for caching)."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            _BASE_URL,
            params=_PARAMS,
            headers=_headers(),
            json={"text": text},
        )
        response.raise_for_status()
        return response.content


async def generate_greeting() -> bytes:
    """Generate and cache the greeting audio at startup (ADR-027)."""
    global _greeting_audio
    _greeting_audio = await _synthesize_full(GREETING_TEXT)
    logger.info("Greeting audio generated — %d bytes", len(_greeting_audio))
    return _greeting_audio


def get_cached_greeting() -> bytes | None:
    """Return the cached greeting audio, or None if not yet generated."""
    return _greeting_audio


async def generate_fillers() -> None:
    """Pre-generate filler phrase audio at startup (sequential)."""
    global _filler_audio
    generated: list[bytes] = []

    for phrase in FILLER_PHRASES:
        try:
            audio = await _synthesize_full(phrase)
            generated.append(audio)
        except Exception:
            logger.warning("Failed to generate filler: %s", phrase)

    _filler_audio = generated
    logger.info(
        "Filler audio generated — %d phrases, %d bytes total",
        len(_filler_audio),
        sum(len(b) for b in _filler_audio),
    )


def get_random_filler() -> bytes | None:
    """Return a random pre-cached filler audio clip, or None."""
    if not _filler_audio:
        return None
    return random.choice(_filler_audio)


async def generate_error_clip() -> bytes:
    """Pre-generate error message audio at startup (ADR-035)."""
    global _error_audio
    _error_audio = await _synthesize_full(ERROR_TEXT)
    logger.info("Error audio generated — %d bytes", len(_error_audio))
    return _error_audio


def get_cached_error_clip() -> bytes | None:
    """Return the cached error audio, or None if not yet generated."""
    return _error_audio
