from typing import Optional
from pydantic import BaseModel

class DoctorCreate(BaseModel):
    user_id: str
    pmdc_number: str
    specialization: str
    bio: Optional[str] = None

class DoctorUpdate(BaseModel):
    specialization: Optional[str] = None
    bio: Optional[str] = None
    is_available: Optional[bool] = None