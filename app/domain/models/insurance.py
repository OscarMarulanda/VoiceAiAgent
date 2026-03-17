from pydantic import BaseModel


class InsurancePlan(BaseModel):
    id: int | None = None
    practice_id: str = "default"
    name: str
    type: str
