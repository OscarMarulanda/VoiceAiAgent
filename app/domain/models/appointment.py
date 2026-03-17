from datetime import datetime
from pydantic import BaseModel


class AppointmentType(BaseModel):
    id: int | None = None
    name: str
    duration_minutes: int
    provider_id: str


class Appointment(BaseModel):
    id: str | None = None
    practice_id: str = "default"
    patient_id: int | None = None
    patient_name: str
    patient_phone: str
    provider_id: str
    appointment_type: str
    starts_at: datetime
    duration_minutes: int
    status: str = "confirmed"
    reason: str | None = None
    notes: str | None = None
    booked_via: str | None = None
    created_at: datetime | None = None


class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    provider_id: str
    available: bool = True
