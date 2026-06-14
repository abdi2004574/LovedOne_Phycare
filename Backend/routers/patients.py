from fastapi import APIRouter, Depends, HTTPException, status
from Backend.database import supabase
from Backend.middleware.auth import get_current_patient

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/me")
def get_my_profile(current_user: dict = Depends(get_current_patient)):
    profile = supabase.table("profiles").select("*").eq("id", current_user["sub"]).single().execute()
    patient = supabase.table("patients").select("*").eq("id", current_user["sub"]).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": profile.data, "patient": patient.data if patient.data else {}}

@router.patch("/me")
def update_my_profile(patch: dict, current_user: dict = Depends(get_current_patient)):
    if not patch:
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase.table("profiles").update(patch).eq("id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    return {"profile": result.data[0]}
