from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role: Literal["patient", "doctor", "admin"] = "patient"
    language: Literal["en", "ur"] = "en"
    pmdc_number: Optional[str] = None
    specialization: Optional[str] = None
    bio: Optional[str] = None
    years_of_experience: Optional[int] = None
    qualifications: Optional[str] = None
    languages: Optional[list[str]] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
