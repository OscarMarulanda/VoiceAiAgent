"""Shared test fixtures — initializes DB pool once for all tests."""

import pytest
import pytest_asyncio
from app.database import init_pool, close_pool


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def db_pool():
    await init_pool()
    yield
    await close_pool()
