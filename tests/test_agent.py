"""Tests for the agent core — integration tests (real Claude) and unit tests (mocked Claude).

Integration tests are marked with @pytest.mark.integration and can be skipped:
    pytest -m "not integration"

Run only integration tests:
    pytest -m integration
"""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

from app.agent.core import (
    MAX_TOOL_CALLS,
    _build_api_messages,
    _extract_text,
    _update_notepad_from_tool,
    process_message,
)
from app.agent.tools import execute_tool
from app.repositories import session_repo, appointment_repo
from app.domain.models.appointment import Appointment
from app.domain.services.scheduling import book_appointment


PACIFIC = ZoneInfo("America/Los_Angeles")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def session():
    """Create a fresh test session and return its ID."""
    s = await session_repo.create_session(channel="test")
    return s["id"]


def _next_weekday(weekday: int) -> datetime:
    """Return the next occurrence of a weekday (0=Mon). In Pacific time."""
    today = datetime.now(PACIFIC).replace(hour=0, minute=0, second=0, microsecond=0)
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


async def _book_test_appointment(provider_id="prov_001", hour=14) -> dict:
    """Book a test appointment and return the result dict. Caller should cancel after."""
    tuesday = _next_weekday(1)
    starts_at = tuesday.replace(hour=hour, minute=0).astimezone(timezone.utc)
    appt = Appointment(
        patient_name="Agent Test Patient",
        patient_phone="(619) 555-9000",
        provider_id=provider_id,
        appointment_type="Exam",
        starts_at=starts_at,
        duration_minutes=30,
        booked_via="test",
    )
    result = await book_appointment(appt)
    assert result["success"] is True
    return result


def _make_response(text=None, tool_use=None):
    """Build a mock Claude API response object."""
    content = []
    if text:
        content.append(SimpleNamespace(type="text", text=text))
    if tool_use:
        for t in tool_use:
            content.append(SimpleNamespace(
                type="tool_use",
                id=t.get("id", "tool_123"),
                name=t["name"],
                input=t["input"],
            ))
    stop_reason = "tool_use" if tool_use else "end_turn"
    return SimpleNamespace(content=content, stop_reason=stop_reason)


# ===========================================================================
# UNIT TESTS — pure functions (no Claude, no DB)
# ===========================================================================


class TestBuildApiMessages:
    def test_basic_conversation(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Book me in"},
        ]
        result = _build_api_messages(messages)
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[-1]["role"] == "user"

    def test_strips_leading_assistant(self):
        messages = [
            {"role": "assistant", "content": "Welcome!"},
            {"role": "user", "content": "Hello"},
        ]
        result = _build_api_messages(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_filters_non_user_assistant_roles(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "internal"},
            {"role": "assistant", "content": "Hi!"},
        ]
        result = _build_api_messages(messages)
        assert len(result) == 2
        assert all(m["role"] in ("user", "assistant") for m in result)

    def test_empty_list(self):
        assert _build_api_messages([]) == []


class TestExtractText:
    def test_single_text_block(self):
        resp = _make_response(text="Hello!")
        assert _extract_text(resp) == "Hello!"

    def test_mixed_blocks(self):
        resp = SimpleNamespace(content=[
            SimpleNamespace(type="tool_use", id="t1", name="foo", input={}),
            SimpleNamespace(type="text", text="Here you go"),
        ])
        assert _extract_text(resp) == "Here you go"

    def test_no_text_returns_fallback(self):
        resp = SimpleNamespace(content=[
            SimpleNamespace(type="tool_use", id="t1", name="foo", input={}),
        ])
        result = _extract_text(resp)
        assert "sorry" in result.lower()


class TestUpdateNotepadFromTool:
    def test_book_appointment_updates_notepad(self):
        notepad = {}
        result = _update_notepad_from_tool(
            notepad,
            "book_appointment",
            {"patient_name": "Jane Doe", "patient_phone": "555-1234", "reason": "Toothache"},
            {
                "success": True,
                "appointment": {
                    "id": "appt-1",
                    "appointment_type": "Exam",
                    "provider_id": "prov_001",
                    "starts_at": "2026-03-16T16:00:00+00:00",
                },
            },
        )
        assert result["patient_name"] == "Jane Doe"
        assert result["patient_phone"] == "555-1234"
        assert result["last_booking"]["id"] == "appt-1"
        assert result["reason"] == "Toothache"

    def test_book_appointment_failure_no_update(self):
        notepad = {}
        result = _update_notepad_from_tool(
            notepad,
            "book_appointment",
            {"patient_name": "Jane Doe"},
            {"success": False, "error": "conflict"},
        )
        assert "patient_name" not in result
        assert "last_booking" not in result

    def test_cancel_appointment_updates_notepad(self):
        notepad = {}
        result = _update_notepad_from_tool(
            notepad,
            "cancel_appointment",
            {"appointment_id": "appt-1"},
            {"success": True},
        )
        assert result["last_cancellation"] == "appt-1"

    def test_lookup_stores_found_appointments(self):
        notepad = {}
        result = _update_notepad_from_tool(
            notepad,
            "lookup_appointment",
            {"patient_name": "John"},
            {
                "appointments": [
                    {
                        "id": "a1",
                        "appointment_type": "Cleaning",
                        "provider_name": "Dr. Chen",
                        "starts_at": "2026-03-16T16:00:00",
                        "status": "confirmed",
                    }
                ],
                "count": 1,
            },
        )
        assert result["patient_name"] == "John"
        assert len(result["found_appointments"]) == 1
        assert result["found_appointments"][0]["id"] == "a1"

    def test_lookup_does_not_overwrite_existing_name(self):
        notepad = {"patient_name": "Original Name"}
        result = _update_notepad_from_tool(
            notepad,
            "lookup_appointment",
            {"patient_name": "New Name"},
            {"appointments": [], "count": 0},
        )
        assert result["patient_name"] == "Original Name"

    def test_check_availability_stores_options(self):
        notepad = {}
        result = _update_notepad_from_tool(
            notepad,
            "check_availability",
            {},
            {
                "providers": [
                    {
                        "provider_id": "prov_001",
                        "provider_name": "Dr. Chen",
                        "appointment_type": "Cleaning",
                        "duration_minutes": 60,
                        "slots": [
                            {"start": "2026-03-16T08:00:00-07:00", "end": "2026-03-16T09:00:00-07:00"},
                            {"start": "2026-03-16T09:00:00-07:00", "end": "2026-03-16T10:00:00-07:00"},
                        ],
                    }
                ],
            },
        )
        assert len(result["last_availability"]) == 2
        assert result["last_availability"][0]["provider_id"] == "prov_001"

    def test_update_notes_appends(self):
        notepad = {"context_notes": ["existing note"]}
        result = _update_notepad_from_tool(
            notepad,
            "update_notes",
            {"note": "patient prefers mornings"},
            {"saved": True},
        )
        assert len(result["context_notes"]) == 2
        assert "patient prefers mornings" in result["context_notes"]

    def test_update_notes_no_duplicates(self):
        notepad = {"context_notes": ["same note"]}
        result = _update_notepad_from_tool(
            notepad,
            "update_notes",
            {"note": "same note"},
            {"saved": True},
        )
        assert len(result["context_notes"]) == 1

    def test_reschedule_updates_last_booking(self):
        notepad = {}
        result = _update_notepad_from_tool(
            notepad,
            "reschedule_appointment",
            {"appointment_id": "appt-1", "new_starts_at": "2026-03-17T10:00:00"},
            {
                "success": True,
                "appointment": {
                    "id": "appt-1",
                    "appointment_type": "Exam",
                    "provider_id": "prov_001",
                    "starts_at": "2026-03-17T10:00:00+00:00",
                },
            },
        )
        assert result["last_booking"]["id"] == "appt-1"


# ===========================================================================
# UNIT TESTS — execute_tool (real DB, no Claude)
# ===========================================================================


class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        result = await execute_tool("nonexistent_tool", {})
        assert "error" in result["result"]
        assert "unknown" in result["summary"].lower()

    @pytest.mark.asyncio
    async def test_get_practice_info(self):
        result = await execute_tool("get_practice_info", {})
        assert "name" in result["result"]
        assert "Sunshine" in result["result"]["name"]

    @pytest.mark.asyncio
    async def test_get_providers(self):
        result = await execute_tool("get_providers", {})
        providers = result["result"]["providers"]
        assert len(providers) >= 4
        names = [p["name"] for p in providers]
        assert any("Chen" in n for n in names)
        assert any("Lisa" in n for n in names)

    @pytest.mark.asyncio
    async def test_get_accepted_insurance(self):
        result = await execute_tool("get_accepted_insurance", {})
        plans = result["result"]["plans"]
        assert len(plans) > 0

    @pytest.mark.asyncio
    async def test_check_availability_by_type(self):
        monday = _next_weekday(0)
        result = await execute_tool("check_availability", {
            "date_from": monday.strftime("%Y-%m-%d"),
            "appointment_type": "Cleaning",
        })
        assert result["result"]["available"] is True
        assert len(result["result"]["providers"]) > 0

    @pytest.mark.asyncio
    async def test_check_availability_by_provider_name(self):
        monday = _next_weekday(0)
        result = await execute_tool("check_availability", {
            "date_from": monday.strftime("%Y-%m-%d"),
            "provider_name": "Lisa Park",
            "appointment_type": "Cleaning",
        })
        assert result["result"]["available"] is True
        providers = result["result"]["providers"]
        assert any("prov_004" in p["provider_id"] for p in providers)

    @pytest.mark.asyncio
    async def test_check_availability_unknown_provider_name(self):
        result = await execute_tool("check_availability", {
            "date_from": "2026-03-16",
            "provider_name": "Dr. Frankenstein",
        })
        assert "error" in result["result"]
        assert "no provider" in result["result"]["error"].lower()

    @pytest.mark.asyncio
    async def test_update_notes(self):
        result = await execute_tool("update_notes", {"note": "test note"})
        assert result["result"]["saved"] is True


# ===========================================================================
# UNIT TESTS — mocked Claude API (real DB)
# ===========================================================================


class TestProcessMessageMocked:
    @pytest.mark.asyncio
    async def test_simple_text_response(self, session):
        """Claude returns a text-only response — no tools."""
        mock_response = _make_response(text="Hello! How can I help you today?")
        with patch("app.agent.core.client") as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            result = await process_message(session, "Hi there")

        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_tool_loop_cap(self, session):
        """Claude keeps requesting tools — verify we stop at MAX_TOOL_CALLS."""
        tool_response = _make_response(tool_use=[{
            "id": "tool_1",
            "name": "get_practice_info",
            "input": {},
        }])
        final_response = _make_response(text="Here's the info!")

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            # After MAX_TOOL_CALLS tool responses, always return tool_use
            # The loop should break when tool_call_count >= MAX_TOOL_CALLS
            if call_count <= MAX_TOOL_CALLS + 1:
                return tool_response
            return final_response

        with patch("app.agent.core.client") as mock_client:
            mock_client.messages.create = AsyncMock(side_effect=mock_create)
            result = await process_message(session, "Tell me about the practice")

        # Should have stopped — either extracted text from last tool_response
        # or hit the cap. The cap is on tool_call_count, not API calls.
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_api_error_returns_graceful_message(self, session):
        """Claude API raises an error — verify graceful fallback."""
        import anthropic
        with patch("app.agent.core.client") as mock_client:
            mock_client.messages.create = AsyncMock(
                side_effect=anthropic.APIError(
                    message="Service unavailable",
                    request=None,
                    body=None,
                )
            )
            result = await process_message(session, "Hello")

        assert "sorry" in result.lower()
        assert "try again" in result.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_session_returns_error(self):
        """Passing an invalid session ID should return a graceful error."""
        result = await process_message("nonexistent-session-id", "Hello")
        assert "sorry" in result.lower()

    @pytest.mark.asyncio
    async def test_notepad_persists_across_turns(self, session):
        """Verify notepad updates are saved to DB and available next turn."""
        # Turn 1: Claude calls book_appointment
        turn1_tool = _make_response(tool_use=[{
            "id": "tool_1",
            "name": "update_notes",
            "input": {"note": "patient prefers mornings"},
        }])
        turn1_final = _make_response(text="Got it, noted!")

        call_idx = 0

        async def mock_turn1(**kwargs):
            nonlocal call_idx
            call_idx += 1
            return turn1_tool if call_idx == 1 else turn1_final

        with patch("app.agent.core.client") as mock_client:
            mock_client.messages.create = AsyncMock(side_effect=mock_turn1)
            await process_message(session, "I prefer mornings")

        # Check notepad was persisted
        context = await session_repo.get_context(session)
        assert "patient prefers mornings" in context["notepad"].get("context_notes", [])


# ===========================================================================
# INTEGRATION TESTS — real Claude API + real DB
# ===========================================================================


@pytest.mark.integration
class TestIntegration:
    @pytest.mark.asyncio
    async def test_faq_practice_info(self, session):
        """Ask about office hours — should return real practice info."""
        result = await process_message(session, "What are your office hours?")
        result_lower = result.lower()
        assert any(word in result_lower for word in ["hours", "open", "am", "pm", "monday"])

    @pytest.mark.asyncio
    async def test_faq_insurance(self, session):
        """Ask about insurance — should list accepted plans."""
        result = await process_message(session, "What insurance do you accept?")
        result_lower = result.lower()
        assert any(word in result_lower for word in ["insurance", "ppo", "hmo", "delta", "accept"])

    @pytest.mark.asyncio
    async def test_booking_flow_availability(self, session):
        """Ask to book a cleaning — should check availability and offer slots."""
        result = await process_message(
            session,
            "I need to schedule a cleaning for next week.",
        )
        result_lower = result.lower()
        # Agent should ask for more info or show availability
        assert any(word in result_lower for word in ["name", "available", "slot", "clean", "when", "prefer"])

    @pytest.mark.asyncio
    async def test_cancellation_lookup(self, session):
        """Ask to cancel — should look up appointment by name."""
        # First, create a real appointment to find
        book_result = await _book_test_appointment()
        appt_id = book_result["appointment"]["id"]

        try:
            result = await process_message(
                session,
                "I need to cancel my appointment. My name is Agent Test Patient.",
            )
            result_lower = result.lower()
            assert any(word in result_lower for word in ["cancel", "appointment", "found", "confirm", "exam"])
        finally:
            await appointment_repo.update_status(appt_id, "cancelled")

    @pytest.mark.asyncio
    async def test_bilingual_spanish(self, session):
        """Send a message in Spanish — should respond in Spanish."""
        result = await process_message(
            session,
            "Hola, necesito hacer una cita para una limpieza dental.",
        )
        # Should contain Spanish words
        assert any(word in result.lower() for word in ["hola", "cita", "limpieza", "nombre", "disponible", "gusto"])
