"""Practice info business logic."""

from app.domain.models.practice import Practice
from app.domain.models.provider import Provider
from app.domain.models.insurance import InsurancePlan
from app.repositories import practice_repo, provider_repo


async def get_practice_info(practice_id: str = "default") -> Practice | None:
    return await practice_repo.get_practice(practice_id)


async def get_providers(practice_id: str = "default") -> list[Provider]:
    return await provider_repo.get_all(practice_id)


async def get_provider(provider_id: str) -> Provider | None:
    return await provider_repo.get_by_id(provider_id)


async def get_accepted_insurance(practice_id: str = "default") -> list[InsurancePlan]:
    return await practice_repo.get_insurance_plans(practice_id)


async def get_appointment_types(provider_id: str | None = None) -> list[dict]:
    return await practice_repo.get_appointment_types(provider_id)
