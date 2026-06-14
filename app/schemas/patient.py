from typing import Any, Optional
from pydantic import BaseModel


class PatientBase(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[dict[str, Any]] = None
    assigned_doctor_id: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: str
    medical_history: dict[str, Any] = {}
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None