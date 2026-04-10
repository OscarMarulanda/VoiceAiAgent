"""Claude API tool definitions and execution dispatcher."""

from datetime import datetime, timedelta, timezone

from app.domain.models.appointment import Appointment
from app.domain.services import scheduling, practice
from app.repositories import provider_repo
from app.utils.timezone import get_practice_tz, utc_to_local

# ---------------------------------------------------------------------------
# Tool schemas (Claude API format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "check_availability",
        "description": (
            "Check available appointment slots over a date range. Search by procedure "
            "type (e.g. 'Cleaning', 'Root Canal') to find slots across all providers "
            "who offer it, or by a specific provider ID, or both. "
            "Returns available time slots grouped by provider. "
            "If the patient says a specific date, search a few days around it "
            "to offer flexible options."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "description": "Start of date range to search (YYYY-MM-DD format).",
                },
                "date_to": {
                    "type": "string",
                    "description": (
                        "End of date range to search (YYYY-MM-DD format). "
                        "Optional — defaults to 3 days after date_from."
                    ),
                },
                "appointment_type": {
                    "type": "string",
                    "description": (
                        "Procedure or appointment type name "
                        "(e.g. 'Cleaning', 'Root Canal', 'Exam'). "
                        "Searches across all providers who offer this procedure. "
                        "You must provide at least one of appointment_type or provider_id."
                    ),
                },
                "provider_name": {
                    "type": "string",
                    "description": (
                        "Provider name to search for (e.g. 'Lisa Park', 'Dr. Chen'). "
                        "Preferred over provider_id — use this when the patient mentions "
                        "a provider by name."
                    ),
                },
                "provider_id": {
                    "type": "string",
                    "description": (
                        "Specific provider ID (e.g. 'prov_004'). Only use if you got the "
                        "exact ID from a previous tool result. Otherwise, use provider_name. "
                        "You must provide at least one of appointment_type, provider_name, or provider_id."
                    ),
                },
            },
            "required": ["date_from"],
        },
    },
    {
        "name": "book_appointment",
        "description": (
            "Book an appointment for a patient. Before calling this you MUST "
            "have just called check_availability — this tool books one of the "
            "slots that was returned. Pass the slot_id from the chosen slot; "
            "provider, time, type, and duration are all inferred from it. "
            "Only call after confirming the details with the patient."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slot_id": {
                    "type": "string",
                    "description": (
                        "The slot_id from a slot returned by the most recent "
                        "check_availability call (e.g. 's1', 's6'). This determines "
                        "the exact time, provider, and duration — never guess or "
                        "construct a timestamp."
                    ),
                },
                "patient_name": {
                    "type": "string",
                    "description": "Full name of the patient.",
                },
                "patient_phone": {
                    "type": "string",
                    "description": "Patient's phone number.",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the visit (optional, patient's own words).",
                },
            },
            "required": ["slot_id", "patient_name", "patient_phone"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to cancel.",
                },
            },
            "required": ["appointment_id"],
        },
    },
    {
        "name": "reschedule_appointment",
        "description": (
            "Reschedule an existing appointment to a new slot. Before calling "
            "this you MUST have just called check_availability for the new "
            "date/time — this tool moves the appointment to one of those slots. "
            "Pass new_slot_id from the chosen slot; never construct a timestamp. "
            "Only call after confirming the new time with the patient."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to reschedule.",
                },
                "new_slot_id": {
                    "type": "string",
                    "description": (
                        "The slot_id from a slot returned by the most recent "
                        "check_availability call (e.g. 's2'). Determines the "
                        "new time — never guess or construct a timestamp."
                    ),
                },
            },
            "required": ["appointment_id", "new_slot_id"],
        },
    },
    {
        "name": "get_practice_info",
        "description": "Get practice information including hours, address, phone number, email, and website.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_providers",
        "description": "List all providers (doctors, hygienists) at the practice with their specialties and available days.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_accepted_insurance",
        "description": "List all insurance plans accepted by the practice.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "lookup_appointment",
        "description": "Look up existing appointments by patient name or phone number. Provide at least one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Patient's full or partial name.",
                },
                "patient_phone": {
                    "type": "string",
                    "description": "Patient's phone number.",
                },
            },
        },
    },
    {
        "name": "update_notes",
        "description": (
            "Save a contextual note about the patient or conversation for your reference. "
            "Use for soft context like preferences, concerns, or things worth remembering. "
            "Do NOT use for info already captured by other tools (name, phone, appointment details)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "The note to save (e.g. 'patient is anxious about dental procedures').",
                },
            },
            "required": ["note"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution dispatcher
# ---------------------------------------------------------------------------

async def execute_tool(
    tool_name: str,
    tool_input: dict,
    notepad: dict | None = None,
) -> dict:
    """Execute a tool call and return the result as a dict.

    Also returns a compact summary for the tool log. The notepad is threaded
    through so booking/rescheduling handlers can resolve slot_ids against
    the most recent check_availability result.

    Returns:
        {"result": <tool output dict>, "summary": <short string for tool log>}
    """
    handler = _TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "result": {"error": f"Unknown tool: {tool_name}"},
            "summary": f"error: unknown tool {tool_name}",
        }

    if tool_name in ("book_appointment", "reschedule_appointment"):
        result = await handler(tool_input, notepad or {})
    else:
        result = await handler(tool_input)
    summary = _summarize_result(tool_name, tool_input, result)
    return {"result": result, "summary": summary}


# ---------------------------------------------------------------------------
# Individual tool handlers
# ---------------------------------------------------------------------------

async def _handle_check_availability(inp: dict) -> dict:
    tz = await get_practice_tz()

    # Interpret dates as practice-local time
    date_from = datetime.fromisoformat(inp["date_from"]).replace(tzinfo=tz)
    date_to = None
    if inp.get("date_to"):
        date_to = datetime.fromisoformat(inp["date_to"]).replace(tzinfo=tz)

    provider_id = inp.get("provider_id")
    appointment_type = inp.get("appointment_type")

    # Resolve provider_name → provider_id if provided
    provider_name_input = inp.get("provider_name")
    if provider_name_input and not provider_id:
        matched = await provider_repo.find_by_name(provider_name_input)
        if matched:
            provider_id = matched.id
        else:
            return {
                "error": (
                    f"No provider found matching '{provider_name_input}'. "
                    "Use get_providers to see available providers."
                ),
            }

    # Procedure-first search: single DB query, date range, all matching providers
    if appointment_type and not provider_id:
        results = await scheduling.get_available_slots_by_type(
            appointment_type, date_from, date_to
        )
        if not results:
            date_to_display = date_to or (date_from + timedelta(days=scheduling.DEFAULT_RANGE_DAYS - 1))
            return {
                "available": False,
                "message": (
                    f"No availability found for '{appointment_type}' "
                    f"from {inp['date_from']} to {date_to_display.strftime('%Y-%m-%d')}. "
                    "Try a wider date range, or use get_providers to see available services."
                ),
            }
        return _build_availability_response(results)

    # Provider-specific search (single day — date_to ignored for simplicity)
    if provider_id:
        duration = 30  # default
        if appointment_type:
            types = await practice.get_appointment_types(provider_id)
            match = next(
                (t for t in types if t["name"].lower() == appointment_type.lower()),
                None,
            )
            if match:
                duration = match["duration_minutes"]

        slots = await scheduling.get_available_slots(provider_id, date_from, duration)
        provider_obj = await practice.get_provider(provider_id)
        provider_name = provider_obj.name if provider_obj else provider_id
        return _build_availability_response([{
            "provider_id": provider_id,
            "provider_name": provider_name,
            "appointment_type": appointment_type or "",
            "duration_minutes": duration,
            "slots": slots,
        }])

    return {"error": "Provide at least appointment_type or provider_id."}


def _build_availability_response(results: list[dict]) -> dict:
    """Assemble the availability tool result with globally unique slot_ids.

    Slot IDs (s1, s2, …) are numbered across all providers in this response,
    so each one uniquely identifies (provider, time, duration, type). The
    agent passes slot_id back to book_appointment / reschedule_appointment
    and the handler resolves it against the session notepad.
    """
    counter = 1
    providers_out: list[dict] = []
    for r in results:
        slots_out = []
        for s in r["slots"]:
            slot_id = f"s{counter}"
            counter += 1
            slots_out.append({
                "slot_id": slot_id,
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
                "day": s.start.strftime("%A"),
                "display": s.start.strftime("%A, %B %d at %I:%M %p"),
            })
        providers_out.append({
            "provider_id": r["provider_id"],
            "provider_name": r["provider_name"],
            "appointment_type": r.get("appointment_type", ""),
            "duration_minutes": r.get("duration_minutes", 30),
            "slots": slots_out,
        })

    if not any(p["slots"] for p in providers_out):
        return {"available": False, "message": "No available slots found."}

    return {"available": True, "providers": providers_out}


async def _handle_book_appointment(inp: dict, notepad: dict) -> dict:
    slot = _resolve_slot(notepad, inp.get("slot_id"))
    if isinstance(slot, dict) and "error" in slot:
        return slot

    # Slot start is already tz-aware practice-local ISO; convert to UTC
    starts_at = datetime.fromisoformat(slot["start"]).astimezone(timezone.utc)

    appointment = Appointment(
        patient_name=inp["patient_name"],
        patient_phone=inp["patient_phone"],
        provider_id=slot["provider_id"],
        appointment_type=slot["appointment_type"],
        starts_at=starts_at,
        duration_minutes=slot["duration_minutes"],
        reason=inp.get("reason"),
        booked_via="agent",
    )
    return await scheduling.book_appointment(appointment)


async def _handle_cancel_appointment(inp: dict) -> dict:
    return await scheduling.cancel_appointment(inp["appointment_id"])


async def _handle_reschedule_appointment(inp: dict, notepad: dict) -> dict:
    slot = _resolve_slot(notepad, inp.get("new_slot_id"))
    if isinstance(slot, dict) and "error" in slot:
        return slot

    new_starts_at = datetime.fromisoformat(slot["start"]).astimezone(timezone.utc)
    return await scheduling.reschedule_appointment(
        inp["appointment_id"], new_starts_at
    )


def _resolve_slot(notepad: dict, slot_id: str | None) -> dict:
    """Look up slot_id in the current session's last_availability.

    Returns the slot dict, or an error dict the agent can act on.
    """
    if not slot_id:
        return {"error": "slot_id is required. Call check_availability first, then pass the slot_id from one of the returned slots."}

    availability = notepad.get("last_availability") or []
    match = next((s for s in availability if s.get("slot_id") == slot_id), None)
    if not match:
        return {
            "error": (
                f"Slot '{slot_id}' is not in the current availability list. "
                "It may be from a stale search. Call check_availability again "
                "for the patient's preferred day and use a slot_id from that result."
            ),
        }
    return match


async def _handle_get_practice_info(_inp: dict) -> dict:
    info = await practice.get_practice_info()
    if not info:
        return {"error": "Practice information not found."}
    return {
        "name": info.name,
        "address": info.address,
        "phone": info.phone,
        "email": info.email,
        "website": info.website,
        "practice_type": info.practice_type,
        "hours": info.hours,
    }


async def _handle_get_providers(_inp: dict) -> dict:
    providers = await practice.get_providers()
    # Also include what appointment types each provider offers
    result = []
    for p in providers:
        types = await practice.get_appointment_types(p.id)
        result.append({
            "id": p.id,
            "name": p.name,
            "specialty": p.specialty,
            "available_days": p.available_days,
            "appointment_types": [t["name"] for t in types],
        })
    return {"providers": result}


async def _handle_get_accepted_insurance(_inp: dict) -> dict:
    plans = await practice.get_accepted_insurance()
    return {
        "plans": [
            {"name": p.name, "type": p.type}
            for p in plans
        ],
    }


async def _handle_lookup_appointment(inp: dict) -> dict:
    tz = await get_practice_tz()
    appointments = await scheduling.lookup_appointments(
        patient_name=inp.get("patient_name"),
        patient_phone=inp.get("patient_phone"),
    )
    # Convert starts_at from UTC to local for display
    for appt in appointments:
        if appt.get("starts_at"):
            utc_dt = datetime.fromisoformat(appt["starts_at"])
            local_dt = utc_to_local(utc_dt, tz)
            appt["starts_at"] = local_dt.isoformat()
            appt["display"] = local_dt.strftime("%A, %B %d at %I:%M %p")
    return {"appointments": appointments, "count": len(appointments)}


async def _handle_update_notes(inp: dict) -> dict:
    # The actual notepad update is handled in core.py.
    # This handler just acknowledges the note.
    return {"saved": True, "note": inp["note"]}


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

_TOOL_HANDLERS = {
    "check_availability": _handle_check_availability,
    "book_appointment": _handle_book_appointment,
    "cancel_appointment": _handle_cancel_appointment,
    "reschedule_appointment": _handle_reschedule_appointment,
    "get_practice_info": _handle_get_practice_info,
    "get_providers": _handle_get_providers,
    "get_accepted_insurance": _handle_get_accepted_insurance,
    "lookup_appointment": _handle_lookup_appointment,
    "update_notes": _handle_update_notes,
}


# ---------------------------------------------------------------------------
# Compact summaries for the tool log
# ---------------------------------------------------------------------------

def _summarize_result(tool_name: str, tool_input: dict, result: dict) -> str:
    """Return a short summary of a tool call for the session tool log."""
    if "error" in result:
        return f"error: {result['error']}"

    match tool_name:
        case "check_availability":
            providers = result.get("providers", [])
            total_slots = sum(len(p.get("slots", [])) for p in providers)
            provider_names = ", ".join(p["provider_name"] for p in providers)
            return f"{total_slots} slots found with {provider_names}" if total_slots else "no slots available"

        case "book_appointment":
            if result.get("success"):
                appt = result["appointment"]
                return f"booked {appt['appointment_type']} with {appt['provider_id']} at {appt['starts_at']}"
            return f"booking failed: {result.get('error', 'unknown')}"

        case "cancel_appointment":
            if result.get("success"):
                return f"cancelled appointment {tool_input.get('appointment_id', '?')}"
            return f"cancel failed: {result.get('error', 'unknown')}"

        case "reschedule_appointment":
            if result.get("success"):
                appt = result["appointment"]
                return f"rescheduled to {appt['starts_at']}"
            return f"reschedule failed: {result.get('error', 'unknown')}"

        case "get_practice_info":
            return f"returned info for {result.get('name', 'practice')}"

        case "get_providers":
            count = len(result.get("providers", []))
            return f"returned {count} providers"

        case "get_accepted_insurance":
            count = len(result.get("plans", []))
            return f"returned {count} insurance plans"

        case "lookup_appointment":
            count = result.get("count", 0)
            return f"found {count} appointment(s)"

        case "update_notes":
            return f"noted: {tool_input.get('note', '')[:60]}"

        case _:
            return str(result)[:80]
