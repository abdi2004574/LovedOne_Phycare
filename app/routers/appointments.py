from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase_admin
from app.middleware.auth import get_current_user
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.post("/", status_code=201)
def book_appointment(body: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(403, "Only patients can book appointments")
    doctor = supabase_admin.table("doctors").select("id, is_verified, is_available").eq("id", body.doctor_id).single().execute()
    if not doctor.data or not doctor.data.get("is_verified"):
        raise HTTPException(400, "Doctor not found or not verified")
    result = supabase_admin.table("appointments").insert({
        "patient_id": current_user["sub"],
        "doctor_id": body.doctor_id,
        "scheduled_at": body.scheduled_at.isoformat(),
        "notes": body.notes,
        "status": "pending",
    }).execute()
    return result.data[0] if result.data else {"id": "new"}

@router.get("/")
def list_appointments(current_user: dict = Depends(get_current_user)):
    uid, role = current_user["sub"], current_user["role"]
    if role == "admin":
        return supabase_admin.table("appointments").select("*").order("scheduled_at", desc=True).execute().data or []
    elif role == "patient":
        return supabase_admin.table("appointments").select("*").eq("patient_id", uid).order("scheduled_at", desc=True).execute().data or []
    else:
        return supabase_admin.table("appointments").select("*").eq("doctor_id", uid).order("scheduled_at", desc=True).execute().data or []

@router.patch("/{appt_id}")
def update_appointment(appt_id: str, body: AppointmentUpdate, current_user: dict = Depends(get_current_user)):
    result = supabase_admin.table("appointments").select("*").eq("id", appt_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Appointment not found")
    appt = result.data
    uid, role = current_user["sub"], current_user["role"]
    if role != "admin" and appt.get("patient_id") != uid and appt.get("doctor_id") != uid:
        raise HTTPException(403, "Not authorized")
    updates = body.model_dump(exclude_none=True)
    if "scheduled_at" in updates:
        updates["scheduled_at"] = updates["scheduled_at"].isoformat()
    updated = supabase_admin.table("appointments").update(updates).eq("id", appt_id).execute()
    return updated.data[0] if updated.data else {"id": appt_id}

@router.delete("/{appt_id}", status_code=204)
def cancel_appointment(appt_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase_admin.table("appointments").select("*").eq("id", appt_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Appointment not found")
    uid, role = current_user["sub"], current_user["role"]
    if role != "admin" and result.data.get("patient_id") != uid:
        raise HTTPException(403, "Not authorized")
    supabase_admin.table("appointments").update({"status": "cancelled"}).eq("id", appt_id).execute()
