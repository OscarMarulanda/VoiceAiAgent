"""Database access for sessions and messages."""

import json
from datetime import datetime

from app.database import execute, fetch, fetchrow, fetchval, get_pool


async def create_session(
    channel: str,
    practice_id: str = "default",
    language: str = "en",
    caller_number: str | None = None,
) -> dict:
    row = await fetchrow(
        """INSERT INTO sessions (channel, practice_id, language, caller_number)
           VALUES ($1, $2, $3, $4)
           RETURNING id, started_at""",
        channel,
        practice_id,
        language,
        caller_number,
    )
    return {"id": row["id"], "started_at": row["started_at"]}


async def get_session(session_id: str) -> dict | None:
    row = await fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
    if not row:
        return None
    return dict(row)


async def end_session(session_id: str) -> None:
    await execute(
        "UPDATE sessions SET status = 'ended', ended_at = NOW() WHERE id = $1",
        session_id,
    )


async def update_language(session_id: str, language: str) -> None:
    await execute(
        "UPDATE sessions SET language = $1 WHERE id = $2",
        language,
        session_id,
    )


async def add_message(session_id: str, role: str, content: str) -> None:
    await execute(
        "INSERT INTO messages (session_id, role, content) VALUES ($1, $2, $3)",
        session_id,
        role,
        content,
    )


async def get_messages(session_id: str) -> list[dict]:
    rows = await fetch(
        "SELECT * FROM messages WHERE session_id = $1 ORDER BY timestamp",
        session_id,
    )
    return [dict(row) for row in rows]


async def get_recent_messages(session_id: str, limit: int = 16) -> list[dict]:
    """Get the most recent messages for a session (for the recent window).

    Default limit=16 corresponds to 8 exchanges (user + assistant).
    Returns in chronological order (oldest first).
    """
    rows = await fetch(
        """SELECT * FROM (
               SELECT * FROM messages
               WHERE session_id = $1
               ORDER BY timestamp DESC
               LIMIT $2
           ) sub ORDER BY timestamp ASC""",
        session_id,
        limit,
    )
    return [dict(row) for row in rows]


async def get_context(session_id: str) -> dict:
    """Get the JSONB notepad context for a session."""
    row = await fetchrow(
        "SELECT context FROM sessions WHERE id = $1",
        session_id,
    )
    if not row or row["context"] is None:
        return {}
    # asyncpg returns JSONB as a string; parse it if needed
    ctx = row["context"]
    if isinstance(ctx, str):
        return json.loads(ctx)
    return ctx


async def update_context(session_id: str, context: dict) -> None:
    """Update the JSONB notepad context for a session."""
    await execute(
        "UPDATE sessions SET context = $1::jsonb WHERE id = $2",
        json.dumps(context),
        session_id,
    )


async def list_sessions(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    if active_only:
        rows = await fetch(
            """SELECT * FROM sessions
               WHERE status = 'active'
               ORDER BY started_at DESC
               LIMIT $1 OFFSET $2""",
            limit,
            offset,
        )
    else:
        rows = await fetch(
            """SELECT * FROM sessions
               ORDER BY started_at DESC
               LIMIT $1 OFFSET $2""",
            limit,
            offset,
        )
    return [dict(row) for row in rows]


async def count_sessions() -> int:
    return await fetchval("SELECT COUNT(*) FROM sessions")


async def cleanup_expired(timeout_minutes: int = 30) -> int:
    result = await execute(
        """UPDATE sessions SET status = 'ended', ended_at = NOW()
           WHERE status = 'active'
           AND started_at < NOW() - ($1 || ' minutes')::interval""",
        str(timeout_minutes),
    )
    # result is like "UPDATE 3"
    parts = result.split()
    return int(parts[1]) if len(parts) > 1 else 0


async def update_metrics(session_id: str, metrics: dict) -> None:
    """Update the metrics JSONB column for a session."""
    await execute(
        "UPDATE sessions SET metrics = $1::jsonb WHERE id = $2",
        json.dumps(metrics),
        session_id,
    )


async def list_sessions_with_counts(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List sessions with message count included. Returns (sessions, total)."""
    where = "WHERE s.status = 'active'" if active_only else ""

    total = await fetchval(
        f"SELECT COUNT(*) FROM sessions s {where}"
    )

    rows = await fetch(
        f"""SELECT s.*,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count
            FROM sessions s
            {where}
            ORDER BY s.started_at DESC
            LIMIT $1 OFFSET $2""",
        limit,
        offset,
    )
    return [dict(row) for row in rows], total


# ---------------------------------------------------------------------------
# Stats queries (for admin dashboard analytics)
# ---------------------------------------------------------------------------

async def count_today(channel: str | None = None) -> int:
    """Count sessions started today, optionally filtered by channel."""
    if channel:
        return await fetchval(
            "SELECT COUNT(*) FROM sessions WHERE started_at::date = CURRENT_DATE AND channel = $1",
            channel,
        )
    return await fetchval(
        "SELECT COUNT(*) FROM sessions WHERE started_at::date = CURRENT_DATE"
    )


async def avg_duration_today_seconds() -> float | None:
    """Average session duration in seconds for today's ended sessions."""
    val = await fetchval(
        """SELECT AVG(EXTRACT(EPOCH FROM (ended_at - started_at)))
           FROM sessions
           WHERE started_at::date = CURRENT_DATE AND ended_at IS NOT NULL"""
    )
    return float(val) if val is not None else None


async def language_breakdown() -> dict[str, int]:
    """Count sessions grouped by language."""
    rows = await fetch(
        "SELECT language, COUNT(*) AS count FROM sessions GROUP BY language ORDER BY count DESC"
    )
    return {row["language"]: row["count"] for row in rows}


async def busiest_day_of_week() -> str | None:
    """Day of week with the most sessions."""
    row = await fetchrow(
        """SELECT TO_CHAR(started_at, 'Day') AS day_name, COUNT(*) AS count
           FROM sessions
           GROUP BY day_name
           ORDER BY count DESC
           LIMIT 1"""
    )
    return row["day_name"].strip() if row else None


async def sessions_per_day_of_week() -> list[dict]:
    """Count sessions grouped by day of week (Mon-Sun)."""
    rows = await fetch(
        """SELECT TRIM(TO_CHAR(started_at, 'Dy')) AS day,
                  EXTRACT(DOW FROM started_at) AS dow,
                  COUNT(*) AS sessions
           FROM sessions
           GROUP BY day, dow
           ORDER BY dow"""
    )
    return [{"day": row["day"], "sessions": row["sessions"]} for row in rows]


async def avg_agent_latency_ms() -> float | None:
    """Average agent latency across sessions that have metrics."""
    val = await fetchval(
        """SELECT AVG((metrics->>'avg_agent_ms')::float)
           FROM sessions
           WHERE metrics->>'avg_agent_ms' IS NOT NULL"""
    )
    return round(float(val), 0) if val is not None else None
