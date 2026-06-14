from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel

AppointmentStatus = Literal["pending", "confirmed", "cancelled", "completed"]

class AppointmentCreate(BaseModel):
    doctor_id: str
    scheduled_at: datetime
    notes: Optional[str] = None

class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    scheduled_at: str
    status: AppointmentStatus
    notes: Optional[str] = None
    created_at: str
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None