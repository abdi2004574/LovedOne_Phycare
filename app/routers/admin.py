from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import supabase, supabase_admin
from app.middleware.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=list)
def list_all_users(role: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), current_user: dict = Depends(get_current_admin)):
    query = supabase_admin.table("profiles")
    if role:
        query = query.eq("role", role)
    result = query.range((page-1)*page_size, page*page_size - 1).execute()
    return result.data or []

@router.get("/stats", response_model=dict)
def get_platform_stats(current_user: dict = Depends(get_current_admin)):
    patients = supabase_admin.table("profiles").select("*", count="exact").eq("role", "patient").execute()
    doctors = supabase_admin.table("profiles").select("*", count="exact").eq("role", "doctor").execute()
    verified_doctors = supabase_admin.table("doctors").select("*", count="exact").eq("is_verified", True).execute()
    active_convs = supabase_admin.table("conversations").select("*", count="exact").eq("status", "active").execute()
    escalated_convs = supabase_admin.table("conversations").select("*", count="exact").eq("status", "escalated").execute()
    appointments = supabase_admin.table("appointments").select("*", count="exact").execute()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages_today = supabase_admin.table("messages").select("*", count="exact").gte("created_at", f"{today}T00:00:00").execute()
    return {
        "total_patients": patients.count if patients.count else 0,
        "total_doctors": doctors.count if doctors.count else 0,
        "verified_doctors": verified_doctors.count if verified_doctors.count else 0,
        "active_conversations": active_convs.count if active_convs.count else 0,
        "escalated_conversations": escalated_convs.count if escalated_convs.count else 0,
        "total_appointments": appointments.count if appointments.count else 0,
        "messages_today": messages_today.count if messages_today.count else 0,
    }

@router.post("/api-keys", response_model=dict)
def create_api_key(name: str, current_user: dict = Depends(get_current_admin)):
    import secrets
    key = secrets.token_urlsafe(32)
    result = supabase_admin.table("api_keys").insert({"name": name, "key_hash": key, "is_active": True}).execute()
    return {"key": key, "id": result.data[0]["id"] if result.data else None}

@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(key_id: str, current_user: dict = Depends(get_current_admin)):
    supabase_admin.table("api_keys").delete().eq("id", key_id).execute()
    return None