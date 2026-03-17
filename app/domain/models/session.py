from datetime import datetime
from pydantic import BaseModel, Field


class Session(BaseModel):
    id: str | None = None
    channel: str
    status: str = "active"
    language: str = "en"
    caller_number: str | None = None
    practice_id: str = "default"
    context: dict = Field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class Message(BaseModel):
    id: int | None = None
    session_id: str
    role: str
    content: str
    timestamp: datetime | None = None
