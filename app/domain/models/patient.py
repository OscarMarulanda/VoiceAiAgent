from datetime import datetime
from pydantic import BaseModel


class Patient(BaseModel):
    id: int | None = None
    name: str
    phone: str
    email: str | None = None
    created_at: datetime | None = None
