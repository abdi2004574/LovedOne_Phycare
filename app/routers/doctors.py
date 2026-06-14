from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import supabase, supabase_admin
from app.middleware.auth import get_current_admin, get_current_user

router = APIRouter(prefix="/doctors", tags=["Doctors"])

@router.get("/", response_model=list)
def list_doctors(specialization: str | None = Query(None), available_only: bool = Query(False)):
    query = supabase_admin.table("profiles").select("*, doctors(*)").eq("role", "doctor")
    if available_only:
        query = query.eq("doctors.is_available", True)
    if specialization:
        query = query.eq("doctors.specialization", specialization)
    result = query.execute()
    return result.data or []

@router.get("/{doctor_id}", response_model=dict)
def get_doctor(doctor_id: str):
    profile = supabase_admin.table("profiles").select("*").eq("id", doctor_id).single().execute()
    doctor = supabase_admin.table("doctors").select("*").eq("id", doctor_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"profile": profile.data, "doctor_data": doctor.data if doctor.data else {}}

@router.get("/me", response_model=dict)
def get_my_profile(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    profile = supabase_admin.table("profiles").select("*").eq("id", current_user["sub"]).single().execute()
    doctor = supabase_admin.table("doctors").select("*").eq("id", current_user["sub"]).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": profile.data, "doctor_data": doctor.data if doctor.data else {}}

@router.patch("/me", response_model=dict)
def update_my_profile(patch: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    if not patch:
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase_admin.table("doctors").update(patch).eq("id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    return {"doctor": result.data[0]}

@router.patch("/{doctor_id}/verify", response_model=dict)
def verify_doctor(doctor_id: str, current_user: dict = Depends(get_current_admin)):
    result = supabase_admin.table("doctors").update({"is_verified": True}).eq("id", doctor_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"doctor": result.data[0]}

@router.delete("/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: str, current_user: dict = Depends(get_current_admin)):
    supabase_admin.table("doctors").delete().eq("id", doctor_id).execute()
    supabase_admin.table("profiles").delete().eq("id", doctor_id).execute()
    return None