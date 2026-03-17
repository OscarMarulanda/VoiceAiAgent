from pydantic import BaseModel


class Provider(BaseModel):
    id: str
    practice_id: str
    name: str
    specialty: str
    available_days: list[str]
    working_hours: dict[str, str] = {}
