"""Database access for patients."""

from app.database import fetch, fetchrow, fetchval
from app.domain.models.patient import Patient


async def get_by_phone(phone: str) -> Patient | None:
    row = await fetchrow("SELECT * FROM patients WHERE phone = $1", phone)
    if not row:
        return None
    return Patient(
        id=row["id"],
        name=row["name"],
        phone=row["phone"],
        email=row["email"],
        created_at=row["created_at"],
    )


async def get_by_name(name: str) -> list[Patient]:
    rows = await fetch(
        "SELECT * FROM patients WHERE LOWER(name) LIKE LOWER($1)",
        f"%{name}%",
    )
    return [
        Patient(
            id=row["id"],
            name=row["name"],
            phone=row["phone"],
            email=row["email"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
