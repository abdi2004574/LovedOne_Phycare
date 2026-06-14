from typing import Any, Optional

from pydantic import BaseModel


class PatientUpdate(BaseModel):
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[dict[str, Any]] = None
