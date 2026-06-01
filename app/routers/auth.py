from fastapi import APIRouter, HTTPException
from app.database import supabase_admin
from app.middleware.auth import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    import time
    user_id = f"acc_{int(time.time()*1000000)}"
    supabase_admin.table("profiles").insert({
        "id": user_id,
        "full_name": body.full_name,
        "phone": body.phone,
        "role": body.role,
        "language": body.language,
    }).execute()
    if body.role == "patient":
        supabase_admin.table("patients").insert({"id": user_id}).execute()
    token = create_access_token({"sub": user_id, "role": body.role, "email": body.email})
    return TokenResponse(access_token=token, user_id=user_id, role=body.role)

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    # Email to profile ID mapping for demo accounts
    email_to_id = {
        "admin@lopc.com": "acc_admin",
        "dr.sarah@lopc.com": "acc_th_sarah",
        "dr.omar@lopc.com": "acc_th_omar",
        "demo@lopc.com": "acc_user_demo",
    }
    
    profile_id = email_to_id.get(body.email)
    if profile_id:
        profile = supabase_admin.table("profiles").select("*").eq("id", profile_id).single().execute()
        if profile.data:
            role = profile.data.get("role", "patient")
            token = create_access_token({"sub": profile_id, "role": role, "email": body.email})
            return TokenResponse(access_token=token, user_id=profile_id, role=role)
    
    raise HTTPException(401, "Invalid credentials")

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}