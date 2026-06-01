from fastapi import APIRouter, Depends, HTTPException, status
from app.database import supabase_admin
from app.middleware.auth import get_current_user, require_role
from app.schemas.patient import PatientUpdate

router = APIRouter(prefix="/patients", tags=["Patients"])

def _get_patient_or_404(patient_id: str) -> dict:
    result = supabase_admin.table("patients").select("*, profiles(*)").eq("id", patient_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Patient not found")
    return result.data

@router.get("/")
def list_patients(_: dict = Depends(require_role("admin"))):
    return supabase_admin.table("patients").select("*, profiles(*)").execute().data or []

@router.get("/{patient_id}")
def get_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "patient" and current_user["sub"] != patient_id:
        raise HTTPException(403, "Not authorized")
    return _get_patient_or_404(patient_id)

@router.put("/{patient_id}")
def update_patient(patient_id: str, body: PatientUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin" and current_user["sub"] != patient_id:
        raise HTTPException(403, "Not authorized")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = supabase_admin.table("patients").update(updates).eq("id", patient_id).execute()
    if not result.data:
        raise HTTPException(404, "Patient not found")
    return result.data[0]

@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, _: dict = Depends(require_role("admin"))):
    _get_patient_or_404(patient_id)
    supabase_admin.table("patients").delete().eq("id", patient_id).execute()
    supabase_admin.table("profiles").delete().eq("id", patient_id).execute()

@router.get("/{patient_id}/conversations")
def get_patient_conversations(patient_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "patient" and current_user["sub"] != patient_id:
        raise HTTPException(403, "Not authorized")
    return supabase_admin.table("conversations").select("*").eq("patient_id", patient_id).order("created_at", desc=True).execute().data or []