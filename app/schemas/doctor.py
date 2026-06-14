from typing import Optional
from pydantic import BaseModel

class DoctorBase(BaseModel):
    specialization: Optional[str] = None
    bio: Optional[str] = None
    is_available: Optional[bool] = True

class DoctorCreate(DoctorBase):
    user_id: str
    pmdc_number: str
    specialization: str

class DoctorUpdate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: str
    pmdc_number: str
    specialization: str
    is_verified: bool
    is_available: bool
    rating: float
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    language: Optional[str] = None
    email: Optional[str] = None