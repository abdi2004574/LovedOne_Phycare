from typing import Literal, Optional
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role: Literal["patient", "doctor"] = "patient"
    language: Literal["en", "ur"] = "en"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str
    language: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ProfileResponse(BaseModel):
    id: str
    full_name: str
    phone: Optional[str] = None
    role: str
    language: str
    avatar_url: Optional[str] = None
    created_at: str