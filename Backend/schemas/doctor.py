from typing import Optional

from pydantic import BaseModel


class DoctorCreate(BaseModel):
    user_id: str
    pmdc_number: str
    specialization: str
    bio: Optional[str] = None
    is_verified: bool = False
    is_available: bool = False


class DoctorUpdate(BaseModel):
    pmdc_number: Optional[str] = None
    specialization: Optional[str] = None
    bio: Optional[str] = None
    is_verified: Optional[bool] = None
    is_available: Optional[bool] = None
    years_of_experience: Optional[int] = None
    qualifications: Optional[str] = None
    languages: Optional[list[str]] = None
