"""Database access for providers."""

import json

from app.database import fetch, fetchrow
from app.domain.models.provider import Provider


async def get_all(practice_id: str = "default") -> list[Provider]:
    rows = await fetch(
        "SELECT * FROM providers WHERE practice_id = $1 ORDER BY name",
        practice_id,
    )
    return [_row_to_provider(row) for row in rows]


async def get_by_id(provider_id: str) -> Provider | None:
    row = await fetchrow("SELECT * FROM providers WHERE id = $1", provider_id)
    if not row:
        return None
    return _row_to_provider(row)


async def find_by_name(name: str, practice_id: str = "default") -> Provider | None:
    """Find a provider by name (case-insensitive partial match).

    Returns the best match or None.
    """
    row = await fetchrow(
        """SELECT * FROM providers
           WHERE practice_id = $1 AND LOWER(name) LIKE LOWER($2)
           ORDER BY name LIMIT 1""",
        practice_id,
        f"%{name}%",
    )
    if not row:
        return None
    return _row_to_provider(row)


def _row_to_provider(row) -> Provider:
    wh = row["working_hours"]
    return Provider(
        id=row["id"],
        practice_id=row["practice_id"],
        name=row["name"],
        specialty=row["specialty"],
        available_days=row["available_days"],
        working_hours=json.loads(wh) if isinstance(wh, str) else wh,
    )
