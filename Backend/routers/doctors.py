from fastapi import APIRouter, Depends, HTTPException, Query, status
from Backend.database import supabase, supabase_admin
from Backend.middleware.auth import get_current_admin, get_current_user

router = APIRouter(prefix="/doctors", tags=["Doctors"])

@router.get("/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    profile = supabase.table("profiles").select("*").eq("id", current_user["sub"]).single().execute()
    doctor = supabase.table("doctors").select("*").eq("id", current_user["sub"]).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": profile.data, "doctor_data": doctor.data if doctor.data else {}}

@router.patch("/me")
def update_my_profile(patch: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access this endpoint")
    if not patch:
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase.table("profiles").update(patch).eq("id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    return {"profile": result.data[0]}

@router.get("/")
def list_doctors(specialization: str | None = Query(None), is_available: bool | None = Query(None), is_verified: bool = Query(True)):
    query = supabase.table("profiles").select("*, doctors(*)").eq("role", "doctor")
    if is_available is not None:
        query = query.eq("doctors.is_available", is_available)
    if specialization:
        query = query.eq("doctors.specialization", specialization)
    result = query.eq("doctors.is_verified", is_verified).execute()
    return result.data

@router.get("/{doctor_id}")
def get_doctor(doctor_id: str):
    profile = supabase.table("profiles").select("*").eq("id", doctor_id).single().execute()
    doctor = supabase.table("doctors").select("*").eq("id", doctor_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"profile": profile.data, "doctor_data": doctor.data if doctor.data else {}}

@router.patch("/{doctor_id}/status")
def update_doctor_status(doctor_id: str, status_update: dict, current_user: dict = Depends(get_current_admin)):
    update_data = {}
    if "is_verified" in status_update:
        update_data["is_verified"] = status_update["is_verified"]
    if "is_available" in status_update:
        update_data["is_available"] = status_update["is_available"]
    if not update_data:
        raise HTTPException(status_code=400, detail="No status update provided")
    result = supabase_admin.table("doctors").update(update_data).eq("id", doctor_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"message": "Doctor status updated", "doctor": result.data[0]}
