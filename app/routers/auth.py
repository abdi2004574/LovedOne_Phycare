from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase, supabase_admin
from app.middleware.auth import create_access_token, get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    auth_resp = supabase.auth.sign_up({"email": body.email, "password": body.password})
    if not auth_resp.user:
        raise HTTPException(400, "Registration failed — email may already be in use")
    user_id = auth_resp.user.id

    supabase_admin.table("profiles").insert({
        "id": user_id,
        "full_name": body.full_name,
        "phone": body.phone,
        "role": body.role,
        "language": body.language,
    }).execute()

    if body.role == "patient":
        supabase_admin.table("patients").insert({"id": user_id}).execute()

    if body.role == "doctor":
        supabase_admin.table("doctors").insert({
            "id": user_id,
            "is_verified": False,
            "is_available": False,
        }).execute()

    token = create_access_token({
        "sub": user_id, "role": body.role,
        "email": body.email, "full_name": body.full_name,
        "language": body.language,
    })
    return TokenResponse(
        access_token=token, user_id=user_id,
        role=body.role, full_name=body.full_name, language=body.language,
    )

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    auth_resp = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
    if not auth_resp.user:
        raise HTTPException(401, "Invalid credentials")
    user_id = auth_resp.user.id
    profile = supabase_admin.table("profiles").select("role, full_name, language").eq("id", user_id).single().execute()
    p = profile.data or {}
    token = create_access_token({
        "sub": user_id, "role": p.get("role","patient"),
        "email": body.email, "full_name": p.get("full_name",""),
        "language": p.get("language","en"),
    })
    return TokenResponse(
        access_token=token, user_id=user_id,
        role=p.get("role","patient"), full_name=p.get("full_name",""),
        language=p.get("language","en"),
    )

@router.get("/me", response_model=TokenResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    profile = supabase_admin.table("profiles").select("*").eq("id", current_user["sub"]).single().execute()
    if not profile.data:
        raise HTTPException(404, "Profile not found")
    p = profile.data
    return {
        "access_token": "",
        "user_id": current_user["sub"],
        "role": p.get("role", "patient"),
        "full_name": p.get("full_name", ""),
        "language": p.get("language", "en"),
    }

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}