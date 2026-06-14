from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import supabase, supabase_admin
from app.middleware.auth import get_current_patient, get_current_user, get_current_admin

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/", response_model=list)
def list_patients(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    result = supabase_admin.table("profiles").select("*, patients(*)").eq("role", "patient").range((page-1)*page_size, page*page_size - 1).execute()
    return result.data or []

@router.get("/{patient_id}", response_model=dict)
def get_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    profile = supabase_admin.table("profiles").select("*").eq("id", patient_id).single().execute()
    patient = supabase_admin.table("patients").select("*").eq("id", patient_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"profile": profile.data, "patient": patient.data if patient.data else {}}

@router.get("/me", response_model=dict)
def get_my_profile(current_user: dict = Depends(get_current_patient)):
    profile = supabase_admin.table("profiles").select("*").eq("id", current_user["sub"]).single().execute()
    patient = supabase_admin.table("patients").select("*").eq("id", current_user["sub"]).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": profile.data, "patient": patient.data if patient.data else {}}

@router.patch("/me", response_model=dict)
def update_my_profile(patch: dict, current_user: dict = Depends(get_current_patient)):
    if not patch:
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase_admin.table("profiles").update(patch).eq("id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    return {"profile": result.data[0]}

@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, current_user: dict = Depends(get_current_admin)):
    supabase_admin.table("patients").delete().eq("id", patient_id).execute()
    supabase_admin.table("profiles").delete().eq("id", patient_id).execute()
    return None