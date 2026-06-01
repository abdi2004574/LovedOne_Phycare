from typing import Any, Optional
from pydantic import BaseModel

class PatientUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[dict[str, Any]] = None
    assigned_doctor_id: Optional[str] = None