"""Scheduling business logic — conflict detection, availability, booking."""

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.domain.models.appointment import Appointment, TimeSlot
from app.repositories import appointment_repo, provider_repo
from app.utils.timezone import get_practice_tz, utc_to_local


# --- Time parsing helpers ---

def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse '8:00 AM' or '5:00 PM' into (hour, minute) in 24h format."""
    time_str = time_str.strip()
    parts = time_str.split()
    time_part = parts[0]
    ampm = parts[1].upper()
    hour, minute = map(int, time_part.split(":"))
    if ampm == "PM" and hour != 12:
        hour += 12
    if ampm == "AM" and hour == 12:
        hour = 0
    return hour, minute


def _get_working_hours(
    working_hours: dict, day_name: str
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Get (start, end) working hours for a specific day."""
    hours_str = working_hours.get(day_name) or working_hours.get("default")
    if not hours_str:
        return None
    start_str, end_str = hours_str.split(" - ")
    return _parse_time(start_str), _parse_time(end_str)


# --- Slot computation (pure logic, no DB) ---

def _parse_booked_ranges(existing_appointments: list[dict]) -> list[tuple[datetime, datetime]]:
    """Convert raw appointment dicts into (start, end) datetime tuples."""
    booked = []
    for appt in existing_appointments:
        appt_start = appt["starts_at"]
        if isinstance(appt_start, str):
            appt_start = datetime.fromisoformat(appt_start)
        if appt_start.tzinfo is None:
            appt_start = appt_start.replace(tzinfo=timezone.utc)
        appt_end = appt_start + timedelta(minutes=appt["duration_minutes"])
        booked.append((appt_start, appt_end))
    return booked


def _compute_slots_for_day(
    provider_id: str,
    date: datetime,
    duration_minutes: int,
    working_hours: dict,
    booked_ranges: list[tuple[datetime, datetime]],
) -> list[TimeSlot]:
    """Compute available slots for a single day. No DB calls."""
    day_name = date.strftime("%A")
    hours = _get_working_hours(working_hours, day_name)
    if not hours:
        return []

    (start_h, start_m), (end_h, end_m) = hours
    tz = date.tzinfo or timezone.utc
    day_start = date.replace(hour=start_h, minute=start_m, second=0, microsecond=0, tzinfo=tz)
    day_end = date.replace(hour=end_h, minute=end_m, second=0, microsecond=0, tzinfo=tz)

    # Skip past slots when computing for today
    now = datetime.now(tz)

    slots = []
    current = day_start
    slot_duration = timedelta(minutes=duration_minutes)

    while current + slot_duration <= day_end:
        if current < now:
            current += timedelta(minutes=30)
            continue
        slot_end = current + slot_duration
        is_available = True
        for booked_start, booked_end in booked_ranges:
            if current < booked_end and slot_end > booked_start:
                is_available = False
                break

        if is_available:
            slots.append(
                TimeSlot(
                    start=current,
                    end=slot_end,
                    provider_id=provider_id,
                    available=True,
                )
            )
        current += timedelta(minutes=30)

    return slots


def _compute_slots(
    provider_id: str,
    date_from: datetime,
    date_to: datetime,
    duration_minutes: int,
    available_days: list[str],
    working_hours: dict,
    existing_appointments: list[dict],
) -> list[TimeSlot]:
    """Compute available time slots across a date range.

    Pure function — no database calls. Iterates over each day in the range,
    checks if the provider works that day, then generates slots minus conflicts.
    All data is already in memory from a single DB query.
    """
    booked_ranges = _parse_booked_ranges(existing_appointments)

    slots = []
    current_date = date_from
    while current_date <= date_to:
        day_name = current_date.strftime("%A")
        if day_name in available_days:
            day_slots = _compute_slots_for_day(
                provider_id=provider_id,
                date=current_date,
                duration_minutes=duration_minutes,
                working_hours=working_hours,
                booked_ranges=booked_ranges,
            )
            slots.extend(day_slots)
        current_date += timedelta(days=1)

    return slots


# --- Availability ---

DEFAULT_RANGE_DAYS = 3


async def get_available_slots(
    provider_id: str,
    date: datetime,
    duration_minutes: int = 30,
) -> list[TimeSlot]:
    """Return available time slots for a provider on a given date.

    The date parameter should be in the practice's local timezone.
    Slots are returned in local time. DB queries use UTC.
    """
    provider = await provider_repo.get_by_id(provider_id)
    if not provider:
        return []

    # Local day boundaries → convert to UTC for DB query
    local_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = date.replace(hour=23, minute=59, second=59, microsecond=0)
    utc_start = local_start.astimezone(timezone.utc)
    utc_end = local_end.astimezone(timezone.utc)

    existing = await appointment_repo.get_confirmed_for_provider_on_date(
        provider_id, utc_start, utc_end
    )

    return _compute_slots(
        provider_id=provider_id,
        date_from=date,
        date_to=date,
        duration_minutes=duration_minutes,
        available_days=provider.available_days,
        working_hours=provider.working_hours,
        existing_appointments=existing,
    )


async def get_available_slots_by_type(
    appointment_type: str,
    date_from: datetime,
    date_to: datetime | None = None,
) -> list[dict]:
    """Find available slots across all providers for a procedure type.

    Single DB query fetches matching providers + their appointments for the
    entire date range. Slot computation iterates over days in Python — no
    additional DB calls.

    Args:
        appointment_type: Procedure name (e.g., "Cleaning", "Root Canal").
        date_from: Start of search range (practice-local timezone).
        date_to: End of search range. Defaults to date_from + DEFAULT_RANGE_DAYS - 1.

    Returns:
        List of dicts grouped by provider, each with their available slots (local time).
    """
    if date_to is None:
        date_to = date_from + timedelta(days=DEFAULT_RANGE_DAYS - 1)

    # Local day boundaries → convert to UTC for DB query
    local_range_start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
    local_range_end = (date_to + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    utc_range_start = local_range_start.astimezone(timezone.utc)
    utc_range_end = local_range_end.astimezone(timezone.utc)

    rows = await appointment_repo.get_providers_and_appointments_by_type(
        appointment_type, utc_range_start, utc_range_end
    )

    if not rows:
        return []

    results = []
    for row in rows:
        working_hours = row["working_hours"]
        if isinstance(working_hours, str):
            working_hours = json.loads(working_hours)

        available_days = row["available_days"]

        existing = row["existing_appointments"]
        if isinstance(existing, str):
            existing = json.loads(existing)

        slots = _compute_slots(
            provider_id=row["provider_id"],
            date_from=date_from,
            date_to=date_to,
            duration_minutes=row["duration_minutes"],
            available_days=available_days,
            working_hours=working_hours,
            existing_appointments=existing,
        )

        if slots:
            results.append({
                "provider_id": row["provider_id"],
                "provider_name": row["provider_name"],
                "appointment_type": row["appointment_type"],
                "duration_minutes": row["duration_minutes"],
                "slots": slots,
            })

    return results


# --- Validation ---

async def _is_within_working_hours(
    provider_id: str, starts_at: datetime, duration_minutes: int
) -> bool:
    provider = await provider_repo.get_by_id(provider_id)
    if not provider:
        return False

    # Convert UTC to practice-local time — working hours are defined in local time
    practice_tz = await get_practice_tz()
    local_start = utc_to_local(starts_at, practice_tz)

    day_name = local_start.strftime("%A")
    if day_name not in provider.available_days:
        return False

    hours = _get_working_hours(provider.working_hours, day_name)
    if not hours:
        return False

    (start_h, start_m), (end_h, end_m) = hours
    day_start = local_start.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    day_end = local_start.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    local_end = local_start + timedelta(minutes=duration_minutes)

    return local_start >= day_start and local_end <= day_end


async def _has_conflict(
    provider_id: str,
    starts_at: datetime,
    duration_minutes: int,
    exclude_id: str | None = None,
) -> bool:
    ends_at = starts_at + timedelta(minutes=duration_minutes)
    count = await appointment_repo.count_conflicts(
        provider_id, starts_at, ends_at, exclude_id
    )
    return count > 0


# --- Operations ---

async def book_appointment(appointment: Appointment) -> dict:
    """Book a new appointment. Returns success/failure dict."""
    if not await _is_within_working_hours(
        appointment.provider_id, appointment.starts_at, appointment.duration_minutes
    ):
        return {
            "success": False,
            "error": "The requested time is outside the provider's working hours.",
        }

    if await _has_conflict(
        appointment.provider_id, appointment.starts_at, appointment.duration_minutes
    ):
        return {
            "success": False,
            "error": "The requested time slot conflicts with an existing appointment.",
        }

    result = await appointment_repo.insert(appointment)

    return {
        "success": True,
        "appointment": {
            "id": result["id"],
            "patient_name": appointment.patient_name,
            "provider_id": appointment.provider_id,
            "appointment_type": appointment.appointment_type,
            "starts_at": appointment.starts_at.isoformat(),
            "duration_minutes": appointment.duration_minutes,
            "status": "confirmed",
        },
    }


async def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an appointment by ID."""
    row = await appointment_repo.get_by_id(appointment_id)
    if not row:
        return {"success": False, "error": "Appointment not found."}

    if row["status"] == "cancelled":
        return {"success": False, "error": "Appointment is already cancelled."}

    await appointment_repo.update_status(appointment_id, "cancelled")
    return {
        "success": True,
        "message": f"Appointment {appointment_id} has been cancelled.",
    }


async def reschedule_appointment(
    appointment_id: str, new_starts_at: datetime
) -> dict:
    """Reschedule an existing appointment to a new time."""
    row = await appointment_repo.get_by_id(appointment_id)
    if not row:
        return {"success": False, "error": "Appointment not found."}

    if row["status"] == "cancelled":
        return {
            "success": False,
            "error": "Cannot reschedule a cancelled appointment.",
        }

    duration = row["duration_minutes"]
    provider_id = row["provider_id"]

    if not await _is_within_working_hours(provider_id, new_starts_at, duration):
        return {
            "success": False,
            "error": "The new time is outside the provider's working hours.",
        }

    if await _has_conflict(
        provider_id, new_starts_at, duration, exclude_id=appointment_id
    ):
        return {
            "success": False,
            "error": "The new time slot conflicts with an existing appointment.",
        }

    await appointment_repo.update_starts_at(appointment_id, new_starts_at)
    return {
        "success": True,
        "appointment": {
            "id": appointment_id,
            "patient_name": row["patient_name"],
            "provider_id": provider_id,
            "appointment_type": row["appointment_type"],
            "starts_at": new_starts_at.isoformat(),
            "duration_minutes": duration,
            "status": "confirmed",
        },
    }


async def lookup_appointments(
    patient_name: str | None = None,
    patient_phone: str | None = None,
) -> list[dict]:
    """Look up appointments by patient name or phone."""
    if patient_phone:
        rows = await appointment_repo.find_by_phone(patient_phone)
    elif patient_name:
        rows = await appointment_repo.find_by_name(patient_name)
    else:
        return []

    return [
        {
            "id": row["id"],
            "patient_name": row["patient_name"],
            "patient_phone": row["patient_phone"],
            "provider_id": row["provider_id"],
            "provider_name": row["provider_name"],
            "appointment_type": row["appointment_type"],
            "starts_at": row["starts_at"].isoformat() if row["starts_at"] else None,
            "duration_minutes": row["duration_minutes"],
            "status": row["status"],
        }
        for row in rows
    ]
