from fastapi import APIRouter, Depends, HTTPException, status
from app.database import supabase_admin
from app.middleware.auth import get_current_user, require_role
from app.schemas.doctor import DoctorCreate, DoctorUpdate

router = APIRouter(prefix="/doctors", tags=["Doctors"])

def _get_doctor_or_404(doctor_id: str) -> dict:
    result = supabase_admin.table("doctors").select("*").eq("id", doctor_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Doctor not found")
    return result.data

@router.get("/")
def list_doctors(specialization: str | None = None, available_only: bool = False):
    query = supabase_admin.table("doctors").select("*").eq("is_verified", True)
    if specialization:
        query = query.eq("specialization", specialization)
    if available_only:
        query = query.eq("is_available", True)
    return query.execute().data or []

@router.get("/{doctor_id}")
def get_doctor(doctor_id: str):
    return _get_doctor_or_404(doctor_id)

@router.post("/", status_code=201)
def create_doctor(body: DoctorCreate, _: dict = Depends(require_role("admin"))):
    supabase_admin.table("profiles").update({"role": "doctor"}).eq("id", body.user_id).execute()
    result = supabase_admin.table("doctors").insert({
        "id": body.user_id,
        "pmdc_number": body.pmdc_number,
        "specialization": body.specialization,
        "bio": body.bio,
    }).execute()
    if not result.data:
        raise HTTPException(400, "Could not create doctor — user may already be registered")
    return result.data[0]

@router.put("/{doctor_id}")
def update_doctor(doctor_id: str, body: DoctorUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin" and current_user["sub"] != doctor_id:
        raise HTTPException(403, "Not authorized")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = supabase_admin.table("doctors").update(updates).eq("id", doctor_id).execute()
    if not result.data:
        raise HTTPException(404, "Doctor not found")
    return result.data[0]

@router.patch("/{doctor_id}/verify")
def verify_doctor(doctor_id: str, _: dict = Depends(require_role("admin"))):
    _get_doctor_or_404(doctor_id)
    result = supabase_admin.table("doctors").update({"is_verified": True}).eq("id", doctor_id).execute()
    return {"message": "Doctor verified", "doctor": result.data[0]} if result.data else {"message": "Doctor verified"}

@router.delete("/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: str, _: dict = Depends(require_role("admin"))):
    _get_doctor_or_404(doctor_id)
    supabase_admin.table("doctors").delete().eq("id", doctor_id).execute()
    supabase_admin.table("profiles").delete().eq("id", doctor_id).execute()