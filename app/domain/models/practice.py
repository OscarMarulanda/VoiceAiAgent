from pydantic import BaseModel


class Practice(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    email: str | None = None
    website: str | None = None
    practice_type: str | None = None
    hours: dict[str, str] = {}
    timezone: str = "America/Los_Angeles"
