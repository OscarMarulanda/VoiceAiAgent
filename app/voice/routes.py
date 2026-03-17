import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response

from app.voice.call_session import CallSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["voice"])


@router.post("/incoming")
async def incoming_call(request: Request):
    """Twilio webhook for incoming calls. Returns TwiML to start a Media Stream."""
    host = request.headers.get("host", "localhost")
    scheme = "wss" if request.url.scheme == "https" else "ws"
    stream_url = f"{scheme}://{host}/twilio/media-stream"

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Connect>"
        f'<Stream url="{stream_url}" />'
        "</Connect>"
        "</Response>"
    )

    return Response(content=twiml, media_type="application/xml")


@router.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    """Twilio Media Stream WebSocket handler.

    Creates a CallSession and delegates all event handling to it.
    """
    await ws.accept()

    session: CallSession | None = None

    try:
        async for raw in ws.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "connected":
                logger.info("Twilio stream connected")

            elif event == "start":
                start_data = msg.get("start", {})
                stream_sid = start_data.get("streamSid")
                call_sid = start_data.get("callSid")
                caller = start_data.get("customParameters", {}).get(
                    "from", "unknown"
                )
                logger.info(
                    "Stream started — stream_sid=%s call_sid=%s caller=%s",
                    stream_sid,
                    call_sid,
                    caller,
                )

                # Create CallSession and start the pipeline
                session = CallSession(twilio_ws=ws, stream_sid=stream_sid)
                await session.start(caller_number=caller)

            elif event == "media":
                if session is not None:
                    await session.handle_audio(msg["media"]["payload"])

            elif event == "stop":
                logger.info("Stream stopped — stream_sid=%s",
                            session.stream_sid if session else "unknown")
                break

    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected")
    except RuntimeError:
        # WebSocket closed by _end_call() while iter_text() is waiting
        logger.info("Twilio WebSocket closed (call ended)")
    except Exception:
        logger.exception("Error in media stream")
    finally:
        if session is not None:
            await session.stop()
