import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database import init_pool, close_pool, fetchval
from app.agent.core import process_message
from app.repositories import session_repo
from app.admin.routes import router as admin_router
from app.chat.routes import router as chat_router
from app.voice.routes import router as voice_router
from app.voice import tts

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_pool()

    # Pre-generate greeting + filler audio (ADR-027)
    try:
        await tts.generate_greeting()
    except Exception:
        logger.warning("Failed to pre-generate greeting — will generate live on first call")

    try:
        await tts.generate_fillers()
    except Exception:
        logger.warning("Failed to pre-generate fillers — agent will respond without fillers")

    # Pre-generate error clip for TTS/STT failure fallback (ADR-035)
    try:
        await tts.generate_error_clip()
    except Exception:
        logger.warning("Failed to pre-generate error clip — TTS failures will be silent")

    yield
    # Shutdown
    await close_pool()


app = FastAPI(
    title="AI Voice & Chat Agent",
    description="AI-powered assistant for healthcare practices",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(voice_router)

# Serve widget static files (ADR-036)
_widget_dir = pathlib.Path(__file__).parent / "widget"
app.mount("/widget", StaticFiles(directory=_widget_dir), name="widget")


@app.get("/health")
async def health():
    db_ok = False
    try:
        result = await fetchval("SELECT 1")
        db_ok = result == 1
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "version": "0.1.0",
        "database": "connected" if db_ok else "disconnected",
    }


# ---------------------------------------------------------------------------
# Temporary test endpoint for Phase 2 development
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str


@app.post("/chat/test", response_model=ChatResponse)
async def chat_test(req: ChatRequest):
    """Temporary endpoint for testing the agent via HTTP.

    If no session_id is provided, creates a new session.
    Send messages to test the full agent flow (Claude + tools + notepad).
    """
    if req.session_id:
        session_id = req.session_id
    else:
        session = await session_repo.create_session(channel="test")
        session_id = session["id"]

    response_text = await process_message(session_id, req.message)
    return ChatResponse(session_id=session_id, response=response_text)
