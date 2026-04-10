"""Core agent logic — the brain of the AI receptionist.

Handles message processing, Claude API interaction, tool execution loop,
notepad management, and conversation history.
"""

import json
import logging

import anthropic

from app.config import settings
from app.agent.prompts import build_system_prompt
from app.agent.tools import TOOLS, execute_tool
from app.repositories import session_repo
from app.utils.timezone import get_practice_tz

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 6
RECENT_MESSAGES_LIMIT = 16  # 8 exchanges (user + assistant)

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_last_turn_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}


def get_last_turn_usage() -> dict[str, int]:
    """Return token usage from the most recent process_message call."""
    return dict(_last_turn_usage)


async def process_message(session_id: str, user_message: str) -> str:
    """Process a user message and return the agent's text response.

    This is the main entry point. It:
    1. Loads session context (notepad + tool log + recent messages)
    2. Adds the user message to DB
    3. Calls Claude with system prompt + context + tools
    4. Executes tool calls in a loop (max MAX_TOOL_CALLS)
    5. Updates notepad from tool results
    6. Saves assistant response to DB
    7. Returns the final text response
    """
    # Load session state
    session = await session_repo.get_session(session_id)
    if not session:
        logger.error("Session %s not found", session_id)
        return "I'm sorry, I'm having trouble with our system. Could you try again?"

    context = await session_repo.get_context(session_id)
    notepad = context.get("notepad", {})
    tool_log = context.get("tool_log", [])

    # Save user message to DB
    await session_repo.add_message(session_id, "user", user_message)

    # Load practice timezone
    practice_tz = await get_practice_tz()

    # Detect channel for prompt customization (voice gets shorter responses)
    channel = session.get("channel", "chat")

    # Load recent message history
    recent_messages = await session_repo.get_recent_messages(
        session_id, RECENT_MESSAGES_LIMIT
    )

    # Build Claude API messages from recent history
    api_messages = _build_api_messages(recent_messages)

    # Build system prompt with notepad context
    system_prompt = build_system_prompt(notepad, tool_log, practice_tz, channel=channel)

    # Call Claude with tool loop
    tool_call_count = 0
    turn_input_tokens = 0
    turn_output_tokens = 0
    while True:
        try:
            response = await client.messages.create(
                model=settings.claude_model,
                max_tokens=1024,
                system=system_prompt,
                messages=api_messages,
                tools=TOOLS,
            )
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            return "I'm sorry, I'm having a little trouble right now. Could you give me a moment and try again?"

        # Track token usage
        turn_input_tokens += response.usage.input_tokens
        turn_output_tokens += response.usage.output_tokens

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_blocks or tool_call_count >= MAX_TOOL_CALLS:
                # Hit the cap or no tool blocks — extract any text and return
                break

            # Add assistant message (with tool_use blocks) to conversation
            api_messages.append({"role": "assistant", "content": response.content})

            # Execute each tool and collect results
            tool_results = []
            for tool_block in tool_blocks:
                tool_call_count += 1
                logger.info(
                    "Tool call #%d: %s(%s)",
                    tool_call_count,
                    tool_block.name,
                    json.dumps(tool_block.input)[:200],
                )

                result = await execute_tool(
                    tool_block.name, tool_block.input, notepad
                )

                # Update notepad from tool results
                notepad = _update_notepad_from_tool(
                    notepad, tool_block.name, tool_block.input, result["result"]
                )

                # Append to tool log
                tool_log.append({
                    "tool": tool_block.name,
                    "summary": result["summary"],
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps(result["result"]),
                })

                if tool_call_count >= MAX_TOOL_CALLS:
                    break

            # Add tool results as a user message (Claude API format)
            api_messages.append({"role": "user", "content": tool_results})

            # Update system prompt with latest notepad state for next iteration
            system_prompt = build_system_prompt(notepad, tool_log, practice_tz, channel=channel)
            continue

        # Claude returned a text response — we're done
        break

    # Log and store token usage for this turn
    logger.info(
        "Token usage — input=%d output=%d total=%d | session=%s",
        turn_input_tokens, turn_output_tokens,
        turn_input_tokens + turn_output_tokens, session_id,
    )
    _last_turn_usage["input_tokens"] = turn_input_tokens
    _last_turn_usage["output_tokens"] = turn_output_tokens

    # Extract final text from response
    assistant_text = _extract_text(response)

    # Save assistant response to DB
    await session_repo.add_message(session_id, "assistant", assistant_text)

    # Persist updated notepad and tool log
    context["notepad"] = notepad
    context["tool_log"] = tool_log
    await session_repo.update_context(session_id, context)

    return assistant_text


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------

def _build_api_messages(recent_messages: list[dict]) -> list[dict]:
    """Convert DB message rows into Claude API message format.

    Only includes user/assistant text messages from the recent window.
    Tool interactions within the current turn are built dynamically
    during the tool loop — they are NOT loaded from DB.
    """
    api_messages = []
    for msg in recent_messages:
        role = msg["role"]
        if role in ("user", "assistant"):
            api_messages.append({
                "role": role,
                "content": msg["content"],
            })

    # Ensure conversation starts with a user message (Claude API requirement)
    if api_messages and api_messages[0]["role"] != "user":
        api_messages = api_messages[1:]

    return api_messages


# ---------------------------------------------------------------------------
# Notepad management
# ---------------------------------------------------------------------------

def _update_notepad_from_tool(
    notepad: dict,
    tool_name: str,
    tool_input: dict,
    tool_result: dict,
) -> dict:
    """Programmatically update notepad fields from tool call results.

    Extracts structured data that we know is important — patient name,
    phone, appointment details, etc. This avoids needing Claude to
    explicitly call update_notes for data we can infer.
    """
    match tool_name:
        case "book_appointment":
            if tool_result.get("success"):
                notepad["patient_name"] = tool_input.get("patient_name", notepad.get("patient_name"))
                notepad["patient_phone"] = tool_input.get("patient_phone", notepad.get("patient_phone"))
                appt = tool_result.get("appointment", {})
                notepad["last_booking"] = {
                    "id": appt.get("id"),
                    "type": appt.get("appointment_type"),
                    "provider": appt.get("provider_id"),
                    "time": appt.get("starts_at"),
                }
                notepad["reason"] = tool_input.get("reason", notepad.get("reason"))

        case "cancel_appointment":
            if tool_result.get("success"):
                notepad["last_cancellation"] = tool_input.get("appointment_id")

        case "reschedule_appointment":
            if tool_result.get("success"):
                appt = tool_result.get("appointment", {})
                notepad["last_booking"] = {
                    "id": appt.get("id"),
                    "type": appt.get("appointment_type"),
                    "provider": appt.get("provider_id"),
                    "time": appt.get("starts_at"),
                }

        case "lookup_appointment":
            name = tool_input.get("patient_name")
            phone = tool_input.get("patient_phone")
            if name:
                notepad["patient_name"] = notepad.get("patient_name") or name
            if phone:
                notepad["patient_phone"] = notepad.get("patient_phone") or phone
            appointments = tool_result.get("appointments", [])
            if appointments:
                notepad["found_appointments"] = [
                    {
                        "id": a["id"],
                        "type": a["appointment_type"],
                        "provider": a.get("provider_name", a.get("provider_id")),
                        "starts_at": a["starts_at"],
                        "status": a["status"],
                    }
                    for a in appointments
                ]

        case "check_availability":
            # Store every returned slot keyed by slot_id so book_appointment /
            # reschedule_appointment can resolve it on the next turn. Never
            # truncate — the whole point of slot_ids is that the agent can
            # pick any slot it presented, not just the first few.
            providers = tool_result.get("providers", [])
            if providers:
                options = []
                for p in providers:
                    for s in p.get("slots", []):
                        options.append({
                            "slot_id": s["slot_id"],
                            "provider_id": p["provider_id"],
                            "provider_name": p["provider_name"],
                            "appointment_type": p.get("appointment_type", ""),
                            "duration_minutes": p.get("duration_minutes", 30),
                            "start": s["start"],
                            "display": s["display"],
                        })
                notepad["last_availability"] = options
            else:
                notepad["last_availability"] = []

        case "update_notes":
            # Append soft context from Claude
            notes = notepad.get("context_notes", [])
            new_note = tool_input.get("note", "")
            if new_note and new_note not in notes:
                notes.append(new_note)
            notepad["context_notes"] = notes

    return notepad


# ---------------------------------------------------------------------------
# Response extraction
# ---------------------------------------------------------------------------

def _extract_text(response) -> str:
    """Extract text content from a Claude API response."""
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    return "\n".join(text_parts) if text_parts else "I'm sorry, I didn't quite catch that. How can I help you?"
