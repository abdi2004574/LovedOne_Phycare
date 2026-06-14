from fastapi import APIRouter, Depends, HTTPException, status
from Backend.database import supabase, supabase_admin
from Backend.middleware.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users")
def list_all_users(current_user: dict = Depends(get_current_admin)):
    result = supabase_admin.table("profiles").select("*").execute()
    return result.data

@router.get("/therapists/pending")
def get_pending_therapists(current_user: dict = Depends(get_current_admin)):
    result = supabase.table("doctors").select("*, profiles(*)").eq("is_verified", False).execute()
    return result.data

@router.patch("/therapists/{therapist_id}/approve")
def approve_therapist(therapist_id: str, current_user: dict = Depends(get_current_admin)):
    result = supabase_admin.table("doctors").update({"is_verified": True}).eq("id", therapist_id).execute()
    return {"message": "Therapist approved", "data": result.data}

@router.patch("/therapists/{therapist_id}/reject")
def reject_therapist(therapist_id: str, current_user: dict = Depends(get_current_admin)):
    result = supabase_admin.table("doctors").update({"is_verified": False}).eq("id", therapist_id).execute()
    return {"message": "Therapist rejected", "data": result.data}

@router.get("/stats")
def get_platform_stats(current_user: dict = Depends(get_current_admin)):
    users = supabase.table("profiles").select("*", count="exact").execute()
    appointments = supabase.table("appointments").select("*", count="exact").execute()
    conversations = supabase.table("conversations").select("*", count="exact").execute()
    return {
        "total_users": users.count if users.count else 0,
        "total_appointments": appointments.count if appointments.count else 0,
        "total_conversations": conversations.count if conversations.count else 0,
    }
