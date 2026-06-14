from fastapi import APIRouter, Depends, HTTPException

from Backend.database import supabase
from Backend.middleware.auth import create_access_token, get_current_user
from Backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def _profile_payload(user: dict, body: RegisterRequest | None = None) -> dict:
    metadata = user.get("user_metadata") or {}
    if body:
        return {
            "id": user["id"],
            "email": body.email,
            "full_name": body.full_name,
            "phone": body.phone,
            "role": body.role,
            "language": body.language,
        }
    return {
        "id": user["id"],
        "email": user.get("email") or metadata.get("email") or "",
        "full_name": metadata.get("full_name") or user.get("email", "").split("@")[0] or "User",
        "phone": metadata.get("phone"),
        "role": metadata.get("role") or "patient",
        "language": metadata.get("language") or "en",
    }


def _ensure_role_table(user_id: str, role: str, body: RegisterRequest | None = None) -> None:
    if role == "patient":
        supabase.table("patients").insert({"id": user_id}).execute()
        return
    if role == "doctor":
        supabase.table("doctors").insert({
            "id": user_id,
            "pmdc_number": body.pmdc_number if body else "",
            "specialization": body.specialization if body else "General Counseling",
            "bio": body.bio if body else "",
            "is_verified": False,
            "is_available": False,
            "years_of_experience": body.years_of_experience if body else None,
            "qualifications": body.qualifications if body else "",
            "languages": body.languages if body else ["English", "Urdu"],
        }).execute()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    auth_response = supabase.auth.sign_up({
        "email": body.email,
        "password": body.password,
        "options": {
            "data": {
                "full_name": body.full_name,
                "phone": body.phone,
                "role": body.role,
                "language": body.language,
                "pmdc_number": body.pmdc_number,
                "specialization": body.specialization,
                "bio": body.bio,
                "years_of_experience": body.years_of_experience,
                "qualifications": body.qualifications,
                "languages": body.languages,
            }
        },
    })
    user = auth_response.user
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create user")

    try:
        supabase.table("profiles").insert(_profile_payload(user, body)).execute()
        _ensure_role_table(user.id, body.role, body)
    except Exception:
        supabase.auth.admin.delete_user(user.id)
        raise HTTPException(status_code=400, detail="Failed to create profile")

    token = create_access_token({"sub": user.id, "role": body.role, "email": body.email})
    return TokenResponse(access_token=token, user_id=user.id, role=body.role)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    auth_response = supabase.auth.sign_in_with_password({
        "email": body.email,
        "password": body.password,
    })
    session = auth_response.session
    if not session or not session.user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = session.user
    profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
    if not profile.data:
        try:
            supabase.table("profiles").insert(_profile_payload(user)).execute()
            _ensure_role_table(user.id, _profile_payload(user).get("role", "patient"))
        except Exception:
            raise HTTPException(status_code=401, detail="Profile is not available")

    role = profile.data.get("role") if profile.data else _profile_payload(user).get("role", "patient")
    token = create_access_token({"sub": user.id, "role": role, "email": body.email})
    return TokenResponse(access_token=token, user_id=user.id, role=role)


@router.get("/me", tags=["Auth"])
def get_me(current_user: dict = Depends(get_current_user)):
    profile = supabase.table("profiles").select("*").eq("id", current_user["sub"]).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.data


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}
