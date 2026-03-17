import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Create the asyncpg connection pool. Call once on app startup."""
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)


async def close_pool() -> None:
    """Close the connection pool. Call on app shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the connection pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def execute(query: str, *args) -> str:
    """Run a query (INSERT, UPDATE, DELETE). Returns command status."""
    pool = get_pool()
    return await pool.execute(query, *args)


async def fetch(query: str, *args) -> list[asyncpg.Record]:
    """Run a query and return all rows."""
    pool = get_pool()
    return await pool.fetch(query, *args)


async def fetchrow(query: str, *args) -> asyncpg.Record | None:
    """Run a query and return a single row."""
    pool = get_pool()
    return await pool.fetchrow(query, *args)


async def fetchval(query: str, *args):
    """Run a query and return a single value."""
    pool = get_pool()
    return await pool.fetchval(query, *args)
