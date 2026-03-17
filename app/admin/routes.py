"""Admin dashboard API endpoints (ADR-038).

Serves the dashboard HTML and provides JSON APIs for sessions,
appointments, providers, and analytics.
"""

import pathlib

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.repositories import session_repo, appointment_repo, provider_repo

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN_DIR = pathlib.Path(__file__).parent


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the admin dashboard HTML page."""
    html_path = _ADMIN_DIR / "dashboard.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Dashboard coming soon</h1><p>Phase 5B</p>")
    return HTMLResponse(html_path.read_text())


# ---------------------------------------------------------------------------
# Sessions API
# ---------------------------------------------------------------------------

@router.get("/api/sessions")
async def list_sessions(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """List sessions with message counts and metrics."""
    sessions, total = await session_repo.list_sessions_with_counts(
        active_only=active_only, limit=limit, offset=offset
    )

    return {
        "sessions": [
            {
                "id": s["id"],
                "channel": s["channel"],
                "started_at": s["started_at"].isoformat() if s.get("started_at") else None,
                "ended_at": s["ended_at"].isoformat() if s.get("ended_at") else None,
                "status": s["status"],
                "language": s.get("language", "en"),
                "caller_number": s.get("caller_number"),
                "message_count": s.get("message_count", 0),
                "metrics": _parse_metrics(s.get("metrics")),
            }
            for s in sessions
        ],
        "total": total,
    }


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get full session detail including conversation and metrics."""
    session = await session_repo.get_session(session_id)
    if not session:
        return {"error": {"code": "session_not_found", "message": f"Session {session_id} not found"}}

    messages = await session_repo.get_messages(session_id)

    return {
        "id": session["id"],
        "channel": session["channel"],
        "started_at": session["started_at"].isoformat() if session.get("started_at") else None,
        "ended_at": session["ended_at"].isoformat() if session.get("ended_at") else None,
        "status": session["status"],
        "language": session.get("language", "en"),
        "caller_number": session.get("caller_number"),
        "messages": [
            {
                "role": m["role"],
                "content": m["content"],
                "timestamp": m["timestamp"].isoformat() if m.get("timestamp") else None,
            }
            for m in messages
        ],
        "metrics": _parse_metrics(session.get("metrics")),
    }


# ---------------------------------------------------------------------------
# Appointments API
# ---------------------------------------------------------------------------

@router.get("/api/appointments")
async def list_appointments(
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
):
    """List appointments with optional filters for calendar/table views."""
    appointments = await appointment_repo.get_all(
        date_from=date_from,
        date_to=date_to,
        provider_id=provider_id,
        status=status,
        search=search,
    )

    return {
        "appointments": [
            {
                "id": a["id"],
                "patient_name": a["patient_name"],
                "patient_phone": a["patient_phone"],
                "provider_id": a["provider_id"],
                "provider_name": a["provider_name"],
                "starts_at": a["starts_at"].isoformat() if a.get("starts_at") else None,
                "duration_minutes": a["duration_minutes"],
                "appointment_type": a["appointment_type"],
                "status": a["status"],
                "booked_via": a.get("booked_via"),
                "created_at": a["created_at"].isoformat() if a.get("created_at") else None,
            }
            for a in appointments
        ],
        "total": len(appointments),
    }


# ---------------------------------------------------------------------------
# Providers API
# ---------------------------------------------------------------------------

@router.get("/api/providers")
async def list_providers():
    """List providers for calendar columns and filter dropdowns."""
    providers = await provider_repo.get_all()

    return {
        "providers": [
            {
                "id": p.id,
                "name": p.name,
                "specialty": p.specialty,
                "available_days": p.available_days,
                "working_hours": p.working_hours,
            }
            for p in providers
        ],
    }


# ---------------------------------------------------------------------------
# Stats / Analytics API
# ---------------------------------------------------------------------------

@router.get("/api/stats")
async def get_stats():
    """Rich analytics for the dashboard."""
    # Today's stats
    total_today = await session_repo.count_today()
    voice_today = await session_repo.count_today(channel="voice")
    chat_today = await session_repo.count_today(channel="chat")
    avg_duration = await session_repo.avg_duration_today_seconds()
    booked_today = await appointment_repo.count_booked_today()
    cancelled_today = await appointment_repo.count_cancelled_today()

    # All-time stats
    total_all_time = await session_repo.count_sessions()
    booked_all_time = await appointment_repo.count_booked_all_time()

    # Breakdowns
    lang_breakdown = await session_repo.language_breakdown()
    busiest_day = await session_repo.busiest_day_of_week()
    sessions_by_day = await session_repo.sessions_per_day_of_week()
    top_procs = await appointment_repo.top_procedures()
    avg_latency = await session_repo.avg_agent_latency_ms()

    return {
        "today": {
            "total_sessions": total_today,
            "voice_sessions": voice_today,
            "chat_sessions": chat_today,
            "appointments_booked": booked_today,
            "appointments_cancelled": cancelled_today,
            "avg_session_duration_seconds": round(avg_duration, 1) if avg_duration else None,
        },
        "all_time": {
            "total_sessions": total_all_time,
            "appointments_booked": booked_all_time,
        },
        "language_breakdown": lang_breakdown,
        "busiest_day_of_week": busiest_day,
        "sessions_by_day": sessions_by_day,
        "top_procedures": [dict(p) for p in top_procs],
        "avg_agent_latency_ms": avg_latency,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_metrics(metrics) -> dict:
    """Normalize metrics from DB (may be dict, str, or None)."""
    if metrics is None:
        return {}
    if isinstance(metrics, str):
        import json
        try:
            return json.loads(metrics)
        except (json.JSONDecodeError, TypeError):
            return {}
    return dict(metrics) if metrics else {}
