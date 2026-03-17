"""Tests for practice info service."""

import pytest

from app.domain.services.practice import (
    get_practice_info,
    get_providers,
    get_provider,
    get_accepted_insurance,
    get_appointment_types,
)


@pytest.mark.asyncio
async def test_get_practice_info():
    practice = await get_practice_info()
    assert practice is not None
    assert practice.name == "Sunshine Dental Care"
    assert "San Diego" in practice.address
    assert practice.hours["Monday"] == "8:00 AM - 5:00 PM"
    assert practice.hours["Sunday"] == "Closed"


@pytest.mark.asyncio
async def test_get_practice_info_invalid():
    practice = await get_practice_info("nonexistent")
    assert practice is None


@pytest.mark.asyncio
async def test_get_providers():
    providers = await get_providers()
    assert len(providers) == 4
    names = [p.name for p in providers]
    assert "Dr. Sarah Chen" in names
    assert "Lisa Park, RDH" in names


@pytest.mark.asyncio
async def test_get_provider_by_id():
    provider = await get_provider("prov_001")
    assert provider is not None
    assert provider.name == "Dr. Sarah Chen"
    assert "Monday" in provider.available_days


@pytest.mark.asyncio
async def test_get_provider_invalid():
    provider = await get_provider("nonexistent")
    assert provider is None


@pytest.mark.asyncio
async def test_get_accepted_insurance():
    plans = await get_accepted_insurance()
    assert len(plans) == 13
    names = [p.name for p in plans]
    assert "Delta Dental PPO" in names
    assert "TRICARE Dental" in names


@pytest.mark.asyncio
async def test_get_appointment_types_all():
    types = await get_appointment_types()
    assert len(types) == 17
    names = [t["name"] for t in types]
    assert "Cleaning" in names
    assert "Root Canal" in names


@pytest.mark.asyncio
async def test_get_appointment_types_by_provider():
    types = await get_appointment_types("prov_003")
    assert len(types) > 0
    for t in types:
        assert t["provider_id"] == "prov_003"
    names = [t["name"] for t in types]
    assert "Child Exam" in names
