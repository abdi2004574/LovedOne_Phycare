from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    doctor_id: str
    scheduled_at: datetime
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    status: Optional[Literal["pending", "confirmed", "cancelled", "completed"]] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None
