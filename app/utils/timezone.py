"""Timezone conversion utilities.

All DB storage is UTC. Conversions happen at application boundaries:
- Inbound (from Claude/patient): local → UTC before storing
- Outbound (to Claude/patient): UTC → local for display
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.repositories import practice_repo

_tz_cache: dict[str, ZoneInfo] = {}


async def get_practice_tz(practice_id: str = "default") -> ZoneInfo:
    """Get the practice's timezone as a ZoneInfo object (cached)."""
    if practice_id in _tz_cache:
        return _tz_cache[practice_id]
    practice = await practice_repo.get_practice(practice_id)
    tz_str = practice.timezone if practice else "America/Los_Angeles"
    tz = ZoneInfo(tz_str)
    _tz_cache[practice_id] = tz
    return tz


def local_to_utc(dt: datetime, tz: ZoneInfo) -> datetime:
    """Interpret a naive datetime as local time and convert to UTC.

    If dt already has tzinfo, converts from that timezone to UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def utc_to_local(dt: datetime, tz: ZoneInfo) -> datetime:
    """Convert a UTC datetime to the practice's local time.

    If dt is naive, assumes UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)
