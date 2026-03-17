"""Database access for appointments."""

from datetime import date, datetime

from app.database import execute, fetch, fetchrow, fetchval
from app.domain.models.appointment import Appointment


async def get_confirmed_for_provider_on_date(
    provider_id: str, day_start: datetime, day_end: datetime
) -> list[dict]:
    """Get all confirmed appointments for a provider in a time range."""
    rows = await fetch(
        """SELECT starts_at, duration_minutes FROM appointments
           WHERE provider_id = $1
           AND starts_at >= $2
           AND starts_at < $3
           AND status = 'confirmed'
           ORDER BY starts_at""",
        provider_id,
        day_start,
        day_end,
    )
    return [
        {"starts_at": row["starts_at"], "duration_minutes": row["duration_minutes"]}
        for row in rows
    ]


async def count_conflicts(
    provider_id: str,
    starts_at: datetime,
    ends_at: datetime,
    exclude_id: str | None = None,
) -> int:
    """Count how many confirmed appointments overlap with the given time range."""
    query = """
        SELECT COUNT(*) FROM appointments
        WHERE provider_id = $1
        AND status = 'confirmed'
        AND starts_at < $2
        AND starts_at + (duration_minutes || ' minutes')::interval > $3
    """
    args: list = [provider_id, ends_at, starts_at]

    if exclude_id:
        query += " AND id != $4"
        args.append(exclude_id)

    return await fetchval(query, *args)


async def insert(appointment: Appointment) -> dict:
    """Insert a new appointment and return its id and created_at."""
    row = await fetchrow(
        """INSERT INTO appointments
           (practice_id, patient_name, patient_phone, provider_id, appointment_type,
            starts_at, duration_minutes, status, reason, notes, booked_via)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
           RETURNING id, created_at""",
        appointment.practice_id,
        appointment.patient_name,
        appointment.patient_phone,
        appointment.provider_id,
        appointment.appointment_type,
        appointment.starts_at,
        appointment.duration_minutes,
        "confirmed",
        appointment.reason,
        appointment.notes,
        appointment.booked_via,
    )
    return {"id": row["id"], "created_at": row["created_at"]}


async def get_by_id(appointment_id: str) -> dict | None:
    """Get an appointment by ID."""
    row = await fetchrow("SELECT * FROM appointments WHERE id = $1", appointment_id)
    if not row:
        return None
    return dict(row)


async def update_status(appointment_id: str, status: str) -> None:
    """Update an appointment's status."""
    await execute(
        "UPDATE appointments SET status = $1 WHERE id = $2",
        status,
        appointment_id,
    )


async def update_starts_at(appointment_id: str, new_starts_at: datetime) -> None:
    """Update an appointment's start time."""
    await execute(
        "UPDATE appointments SET starts_at = $1 WHERE id = $2",
        new_starts_at,
        appointment_id,
    )


async def find_by_phone(patient_phone: str) -> list[dict]:
    """Find confirmed appointments by patient phone."""
    rows = await fetch(
        """SELECT a.*, p.name as provider_name
           FROM appointments a
           JOIN providers p ON p.id = a.provider_id
           WHERE a.patient_phone = $1 AND a.status = 'confirmed'
           ORDER BY a.starts_at""",
        patient_phone,
    )
    return [dict(row) for row in rows]


async def find_by_name(patient_name: str) -> list[dict]:
    """Find confirmed appointments by patient name (partial match)."""
    rows = await fetch(
        """SELECT a.*, p.name as provider_name
           FROM appointments a
           JOIN providers p ON p.id = a.provider_id
           WHERE LOWER(a.patient_name) LIKE LOWER($1) AND a.status = 'confirmed'
           ORDER BY a.starts_at""",
        f"%{patient_name}%",
    )
    return [dict(row) for row in rows]


async def get_providers_and_appointments_by_type(
    appointment_type: str, day_start: datetime, day_end: datetime
) -> list[dict]:
    """Single query: find providers who offer a procedure type AND their
    confirmed appointments for the given date range.

    Returns one row per provider, with their appointments embedded as a JSON
    array (empty array if no appointments that day).
    """
    rows = await fetch(
        """
        SELECT
            p.id AS provider_id,
            p.name AS provider_name,
            p.available_days,
            p.working_hours,
            at.name AS appointment_type,
            at.duration_minutes,
            COALESCE(
                json_agg(
                    json_build_object(
                        'starts_at', a.starts_at,
                        'duration_minutes', a.duration_minutes
                    )
                ) FILTER (WHERE a.id IS NOT NULL),
                '[]'::json
            ) AS existing_appointments
        FROM appointment_types at
        JOIN providers p ON p.id = at.provider_id
        LEFT JOIN appointments a
            ON a.provider_id = p.id
            AND a.starts_at >= $2
            AND a.starts_at < $3
            AND a.status = 'confirmed'
        WHERE LOWER(at.name) LIKE '%%' || LOWER($1) || '%%'
        GROUP BY p.id, p.name, p.available_days, p.working_hours,
                 at.name, at.duration_minutes
        """,
        appointment_type,
        day_start,
        day_end,
    )
    return [dict(row) for row in rows]


async def get_all(
    practice_id: str = "default",
    date_from: str | None = None,
    date_to: str | None = None,
    provider_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """Get all appointments with optional filters. For admin dashboard."""
    query = """
        SELECT a.*, p.name as provider_name
        FROM appointments a
        JOIN providers p ON p.id = a.provider_id
        WHERE a.practice_id = $1
    """
    args: list = [practice_id]
    idx = 2

    if date_from:
        query += f" AND a.starts_at::date >= ${idx}"
        args.append(date.fromisoformat(date_from))
        idx += 1

    if date_to:
        query += f" AND a.starts_at::date <= ${idx}"
        args.append(date.fromisoformat(date_to))
        idx += 1

    if provider_id:
        query += f" AND a.provider_id = ${idx}"
        args.append(provider_id)
        idx += 1

    if status:
        query += f" AND a.status = ${idx}"
        args.append(status)
        idx += 1

    if search:
        query += f" AND LOWER(a.patient_name) LIKE LOWER(${idx})"
        args.append(f"%{search}%")
        idx += 1

    query += " ORDER BY a.starts_at"
    rows = await fetch(query, *args)
    return [dict(row) for row in rows]


async def count_booked_today() -> int:
    """Count appointments booked (created) today."""
    return await fetchval(
        "SELECT COUNT(*) FROM appointments WHERE created_at::date = CURRENT_DATE AND status = 'confirmed'"
    )


async def count_cancelled_today() -> int:
    """Count appointments cancelled today."""
    return await fetchval(
        "SELECT COUNT(*) FROM appointments WHERE updated_at::date = CURRENT_DATE AND status = 'cancelled'"
    )


async def count_booked_all_time() -> int:
    """Count all confirmed appointments ever."""
    return await fetchval(
        "SELECT COUNT(*) FROM appointments WHERE status = 'confirmed'"
    )


async def top_procedures(limit: int = 5) -> list[dict]:
    """Top appointment types by frequency."""
    rows = await fetch(
        """SELECT appointment_type AS name, COUNT(*) AS count
           FROM appointments
           WHERE status = 'confirmed'
           GROUP BY appointment_type
           ORDER BY count DESC
           LIMIT $1""",
        limit,
    )
    return [dict(row) for row in rows]
