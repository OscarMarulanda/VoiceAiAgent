"""Chat WebSocket endpoint for the embeddable widget.

Handles WebSocket lifecycle: connect → welcome → message loop → disconnect.
Integrates with the same Agent Core used by the voice pipeline.
"""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.core import process_message, get_last_turn_usage
from app.repositories import session_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Ping timeout: close connection if no ping received within this window
PING_TIMEOUT_S = 60
# Agent processing timeout
AGENT_TIMEOUT_S = 30


@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    """WebSocket endpoint for the chat widget.

    Protocol (see docs/CHAT_WIDGET.md):
      Client → Server: {"type": "message", "content": "...", "session_id": "..."}
      Client → Server: {"type": "ping"}
      Server → Client: {"type": "welcome", "content": "...", "session_id": "..."}
      Server → Client: {"type": "message", "content": "...", "session_id": "..."}
      Server → Client: {"type": "typing", "status": true/false}
      Server → Client: {"type": "error", "content": "..."}
      Server → Client: {"type": "pong"}
    """
    await ws.accept()

    session_id: str | None = None
    last_ping = time.monotonic()
    # Metrics accumulation (ADR-038)
    _turns = 0
    _agent_ms_total = 0.0
    _input_tokens = 0
    _output_tokens = 0

    # Start ping timeout watcher
    ping_task = asyncio.create_task(_ping_watchdog(ws, lambda: last_ping))

    try:
        async for raw in ws.iter_text():
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send(ws, "error", content="Invalid message format.")
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                last_ping = time.monotonic()
                await _send(ws, "pong")

            elif msg_type == "message":
                content = (msg.get("content") or "").strip()
                if not content:
                    continue

                # Create or reuse session
                client_session_id = msg.get("session_id")
                if session_id is None:
                    session_id = await _resolve_session(client_session_id)

                # Send typing indicator
                await _send(ws, "typing", status=True)

                # Process through Agent Core
                try:
                    t0 = time.monotonic()
                    response_text = await asyncio.wait_for(
                        process_message(session_id, content),
                        timeout=AGENT_TIMEOUT_S,
                    )
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    logger.info(
                        "Chat response — session=%s elapsed=%dms",
                        session_id,
                        elapsed_ms,
                    )
                    # Accumulate metrics (ADR-038)
                    _turns += 1
                    _agent_ms_total += elapsed_ms
                    usage = get_last_turn_usage()
                    _input_tokens += usage["input_tokens"]
                    _output_tokens += usage["output_tokens"]
                except asyncio.TimeoutError:
                    logger.warning("Agent timeout — session=%s", session_id)
                    response_text = (
                        "I'm sorry, I'm taking longer than expected. "
                        "Could you try again?"
                    )
                except Exception:
                    logger.exception("Agent error — session=%s", session_id)
                    response_text = (
                        "I'm sorry, I'm having trouble right now. "
                        "Please try again in a moment."
                    )

                # Stop typing, send response
                await _send(ws, "typing", status=False)
                await _send(ws, "message", content=response_text, session_id=session_id)

            else:
                await _send(ws, "error", content=f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected — session=%s", session_id)
    except Exception:
        logger.exception("Chat WebSocket error — session=%s", session_id)
    finally:
        ping_task.cancel()
        if session_id:
            # Persist chat metrics (ADR-038)
            try:
                ctx = await session_repo.get_context(session_id)
                tool_log = ctx.get("tool_log", [])
                notepad = ctx.get("notepad", {})
                metrics = {
                    "total_turns": _turns,
                    "avg_agent_ms": round(_agent_ms_total / _turns, 0) if _turns > 0 else None,
                    "tools_used": sorted({e["tool"] for e in tool_log if "tool" in e}),
                    "appointment_booked": bool(notepad.get("last_booking")),
                    "outcome": "completed",
                    "input_tokens": _input_tokens,
                    "output_tokens": _output_tokens,
                    "total_tokens": _input_tokens + _output_tokens,
                }
                await session_repo.update_metrics(session_id, metrics)
            except Exception:
                logger.exception("Failed to persist chat metrics — session=%s", session_id)

            await session_repo.end_session(session_id)
            logger.info("Chat session ended — session=%s", session_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _resolve_session(client_session_id: str | None) -> str:
    """Reuse an existing active session or create a new one.

    If the client provides a session_id (from sessionStorage after reconnect),
    verify it exists and is still active. Otherwise create a fresh session.
    """
    if client_session_id:
        existing = await session_repo.get_session(client_session_id)
        if existing and existing.get("status") == "active":
            logger.info("Chat session resumed — session=%s", client_session_id)
            return client_session_id

    session = await session_repo.create_session(channel="chat")
    logger.info("Chat session created — session=%s", session["id"])
    return session["id"]


async def _send(ws: WebSocket, msg_type: str, **kwargs) -> None:
    """Send a JSON message to the client."""
    payload = {"type": msg_type, **kwargs}
    try:
        await ws.send_text(json.dumps(payload))
    except Exception:
        pass  # Connection already closed


async def _ping_watchdog(ws: WebSocket, get_last_ping) -> None:
    """Close the WebSocket if no ping is received within PING_TIMEOUT_S."""
    try:
        while True:
            await asyncio.sleep(15)
            elapsed = time.monotonic() - get_last_ping()
            if elapsed > PING_TIMEOUT_S:
                logger.info("Chat ping timeout — closing connection")
                await ws.close(code=1000, reason="Ping timeout")
                return
    except asyncio.CancelledError:
        pass
    except Exception:
        pass  # WebSocket already closed
