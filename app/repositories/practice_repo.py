"""Database access for practice info."""

import json

from app.database import fetch, fetchrow
from app.domain.models.practice import Practice
from app.domain.models.insurance import InsurancePlan


async def get_practice(practice_id: str = "default") -> Practice | None:
    row = await fetchrow("SELECT * FROM practices WHERE id = $1", practice_id)
    if not row:
        return None
    return Practice(
        id=row["id"],
        name=row["name"],
        address=row["address"],
        phone=row["phone"],
        email=row["email"],
        website=row["website"],
        practice_type=row["practice_type"],
        hours=json.loads(row["hours"]) if isinstance(row["hours"], str) else row["hours"],
        timezone=row["timezone"],
    )


async def get_insurance_plans(practice_id: str = "default") -> list[InsurancePlan]:
    rows = await fetch(
        "SELECT * FROM insurance_plans WHERE practice_id = $1 ORDER BY name",
        practice_id,
    )
    return [
        InsurancePlan(
            id=row["id"],
            practice_id=row["practice_id"],
            name=row["name"],
            type=row["type"],
        )
        for row in rows
    ]


async def get_appointment_types(provider_id: str | None = None) -> list[dict]:
    if provider_id:
        rows = await fetch(
            """SELECT at.name, at.duration_minutes, at.provider_id, p.name as provider_name
               FROM appointment_types at
               JOIN providers p ON p.id = at.provider_id
               WHERE at.provider_id = $1
               ORDER BY at.name""",
            provider_id,
        )
    else:
        rows = await fetch(
            """SELECT at.name, at.duration_minutes, at.provider_id, p.name as provider_name
               FROM appointment_types at
               JOIN providers p ON p.id = at.provider_id
               ORDER BY at.name""",
        )
    return [
        {
            "name": row["name"],
            "duration_minutes": row["duration_minutes"],
            "provider_id": row["provider_id"],
            "provider_name": row["provider_name"],
        }
        for row in rows
    ]
