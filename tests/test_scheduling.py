"""Tests for scheduling service — availability, booking, conflicts, cancellation, rescheduling."""

import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.domain.services.scheduling import (
    get_available_slots,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    lookup_appointments,
)
from app.domain.models.appointment import Appointment
from app.repositories import appointment_repo

# Practice timezone — matches seed data
PACIFIC = ZoneInfo("America/Los_Angeles")


# --- Helpers ---

def _next_weekday(weekday: int) -> datetime:
    """Return the next occurrence of a weekday (0=Mon, 5=Sat). Always in the future.
    Returns in the practice's local timezone (Pacific).
    """
    today = datetime.now(PACIFIC).replace(hour=0, minute=0, second=0, microsecond=0)
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def _next_monday() -> datetime:
    return _next_weekday(0)


def _next_tuesday() -> datetime:
    return _next_weekday(1)


def _next_sunday() -> datetime:
    return _next_weekday(6)


# --- Availability ---

@pytest.mark.asyncio
async def test_available_slots_returns_slots_on_working_day():
    monday = _next_monday()
    slots = await get_available_slots("prov_001", monday, 30)
    assert len(slots) > 0
    for slot in slots:
        assert slot.provider_id == "prov_001"
        assert slot.available is True


@pytest.mark.asyncio
async def test_available_slots_empty_on_non_working_day():
    """Dr. Chen doesn't work Sundays."""
    sunday = _next_sunday()
    slots = await get_available_slots("prov_001", sunday, 30)
    assert len(slots) == 0


@pytest.mark.asyncio
async def test_available_slots_empty_for_invalid_provider():
    monday = _next_monday()
    slots = await get_available_slots("nonexistent", monday, 30)
    assert len(slots) == 0


@pytest.mark.asyncio
async def test_available_slots_respects_existing_appointments():
    """Slots occupied by seeded appointments should not appear."""
    monday = _next_monday()
    # Dr. Chen has a seeded Exam at 9:00 AM on Monday
    slots = await get_available_slots("prov_001", monday, 30)
    slot_starts = [s.start.hour * 60 + s.start.minute for s in slots]
    # 9:00 AM = 540 minutes. Should not be in available slots.
    assert 540 not in slot_starts


@pytest.mark.asyncio
async def test_available_slots_longer_duration_fewer_slots():
    """Requesting 90-min slots should return fewer slots than 30-min."""
    monday = _next_monday()
    slots_30 = await get_available_slots("prov_001", monday, 30)
    slots_90 = await get_available_slots("prov_001", monday, 90)
    assert len(slots_90) < len(slots_30)


# --- Booking ---

@pytest.mark.asyncio
async def test_book_appointment_success():
    tuesday = _next_tuesday()
    starts_at = tuesday.replace(hour=14, minute=0).astimezone(timezone.utc)

    appt = Appointment(
        patient_name="Test Patient",
        patient_phone="(619) 555-9999",
        provider_id="prov_002",
        appointment_type="Cosmetic Consultation",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    result = await book_appointment(appt)
    assert result["success"] is True
    assert result["appointment"]["patient_name"] == "Test Patient"
    assert result["appointment"]["status"] == "confirmed"

    # Cleanup
    await appointment_repo.update_status(result["appointment"]["id"], "cancelled")


@pytest.mark.asyncio
async def test_book_appointment_conflict():
    """Booking at the same time as an existing appointment should fail."""
    tuesday = _next_tuesday()
    starts_at = tuesday.replace(hour=15, minute=0).astimezone(timezone.utc)

    appt1 = Appointment(
        patient_name="Conflict Test A",
        patient_phone="(619) 555-8881",
        provider_id="prov_002",
        appointment_type="Exam",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    result1 = await book_appointment(appt1)
    assert result1["success"] is True

    appt2 = Appointment(
        patient_name="Conflict Test B",
        patient_phone="(619) 555-8882",
        provider_id="prov_002",
        appointment_type="Exam",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    result2 = await book_appointment(appt2)
    assert result2["success"] is False
    assert "conflicts" in result2["error"].lower()

    # Cleanup
    await appointment_repo.update_status(result1["appointment"]["id"], "cancelled")


@pytest.mark.asyncio
async def test_book_appointment_outside_hours():
    """Booking at 6 AM (before opening) should fail."""
    tuesday = _next_tuesday()
    starts_at = tuesday.replace(hour=6, minute=0).astimezone(timezone.utc)

    appt = Appointment(
        patient_name="Early Bird",
        patient_phone="(619) 555-7777",
        provider_id="prov_001",
        appointment_type="Exam",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    result = await book_appointment(appt)
    assert result["success"] is False
    assert "working hours" in result["error"].lower()


@pytest.mark.asyncio
async def test_book_appointment_on_day_off():
    """Dr. Rodriguez doesn't work Saturdays."""
    saturday = _next_weekday(5)
    starts_at = saturday.replace(hour=10, minute=0).astimezone(timezone.utc)

    appt = Appointment(
        patient_name="Weekend Warrior",
        patient_phone="(619) 555-6666",
        provider_id="prov_002",
        appointment_type="Exam",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    result = await book_appointment(appt)
    assert result["success"] is False


# --- Cancellation ---

@pytest.mark.asyncio
async def test_cancel_appointment_success():
    tuesday = _next_tuesday()
    starts_at = tuesday.replace(hour=16, minute=0).astimezone(timezone.utc)

    appt = Appointment(
        patient_name="Cancel Test",
        patient_phone="(619) 555-5555",
        provider_id="prov_001",
        appointment_type="Exam",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    book_result = await book_appointment(appt)
    assert book_result["success"] is True
    appt_id = book_result["appointment"]["id"]

    cancel_result = await cancel_appointment(appt_id)
    assert cancel_result["success"] is True


@pytest.mark.asyncio
async def test_cancel_nonexistent_appointment():
    result = await cancel_appointment("nonexistent-id")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_cancel_already_cancelled():
    tuesday = _next_tuesday()
    starts_at = tuesday.replace(hour=16, minute=30).astimezone(timezone.utc)

    appt = Appointment(
        patient_name="Double Cancel",
        patient_phone="(619) 555-4444",
        provider_id="prov_001",
        appointment_type="Exam",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    book_result = await book_appointment(appt)
    appt_id = book_result["appointment"]["id"]

    await cancel_appointment(appt_id)
    result = await cancel_appointment(appt_id)
    assert result["success"] is False
    assert "already cancelled" in result["error"].lower()


# --- Rescheduling ---

@pytest.mark.asyncio
async def test_reschedule_success():
    tuesday = _next_tuesday()
    original_time = tuesday.replace(hour=11, minute=0).astimezone(timezone.utc)
    new_time = tuesday.replace(hour=13, minute=0).astimezone(timezone.utc)

    appt = Appointment(
        patient_name="Reschedule Test",
        patient_phone="(619) 555-3333",
        provider_id="prov_002",
        appointment_type="Exam",
        starts_at=original_time,
        duration_minutes=30,
        booked_via="test",
    )
    book_result = await book_appointment(appt)
    assert book_result["success"] is True
    appt_id = book_result["appointment"]["id"]

    reschedule_result = await reschedule_appointment(appt_id, new_time)
    assert reschedule_result["success"] is True
    assert reschedule_result["appointment"]["starts_at"] == new_time.isoformat()

    # Cleanup
    await appointment_repo.update_status(appt_id, "cancelled")


@pytest.mark.asyncio
async def test_reschedule_to_conflicting_time():
    tuesday = _next_tuesday()
    time_a = tuesday.replace(hour=10, minute=0).astimezone(timezone.utc)
    time_b = tuesday.replace(hour=10, minute=30).astimezone(timezone.utc)

    appt_a = Appointment(
        patient_name="Reschedule Conflict A",
        patient_phone="(619) 555-2221",
        provider_id="prov_002",
        appointment_type="Exam",
        starts_at=time_a,
        duration_minutes=30,
        booked_via="test",
    )
    appt_b = Appointment(
        patient_name="Reschedule Conflict B",
        patient_phone="(619) 555-2222",
        provider_id="prov_002",
        appointment_type="Exam",
        starts_at=time_b,
        duration_minutes=30,
        booked_via="test",
    )

    result_a = await book_appointment(appt_a)
    result_b = await book_appointment(appt_b)
    assert result_a["success"] is True
    assert result_b["success"] is True

    # Try to reschedule B to A's time
    reschedule_result = await reschedule_appointment(
        result_b["appointment"]["id"], time_a
    )
    assert reschedule_result["success"] is False
    assert "conflicts" in reschedule_result["error"].lower()

    # Cleanup
    await appointment_repo.update_status(result_a["appointment"]["id"], "cancelled")
    await appointment_repo.update_status(result_b["appointment"]["id"], "cancelled")


# --- Lookup ---

@pytest.mark.asyncio
async def test_lookup_by_name():
    results = await lookup_appointments(patient_name="John Smith")
    assert len(results) >= 1
    assert results[0]["patient_name"] == "John Smith"


@pytest.mark.asyncio
async def test_lookup_by_phone():
    results = await lookup_appointments(patient_phone="(619) 555-1001")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_lookup_partial_name():
    results = await lookup_appointments(patient_name="Garcia")
    assert len(results) >= 1
    assert "Garcia" in results[0]["patient_name"]


@pytest.mark.asyncio
async def test_lookup_no_match():
    results = await lookup_appointments(patient_name="Nonexistent Person")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_lookup_no_params():
    results = await lookup_appointments()
    assert len(results) == 0
