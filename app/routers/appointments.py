from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import supabase, supabase_admin
from app.middleware.auth import get_current_patient, get_current_user
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.get("/", response_model=list[AppointmentResponse])
def get_appointments(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    role = current_user["role"]
    query = supabase_admin.table("appointments").select("*, profiles!patient_id(full_name), doctors!doctor_id(full_name)")
    if role == "patient":
        query = query.eq("patient_id", user_id)
    elif role == "doctor":
        query = query.eq("doctor_id", user_id)
    result = query.range((page-1)*page_size, page*page_size - 1).execute()
    appointments = []
    for appt in (result.data or []):
        appointments.append({
            **appt,
            "patient_name": appt.get("profiles", {}).get("full_name") if appt.get("profiles") else None,
            "doctor_name": appt.get("doctors", {}).get("full_name") if appt.get("doctors") else None,
        })
    return appointments

@router.post("/", response_model=AppointmentResponse, status_code=201)
def create_appointment(data: AppointmentCreate, current_user: dict = Depends(get_current_patient)):
    doctor_id = data.doctor_id
    scheduled_at = data.scheduled_at
    if not doctor_id or not scheduled_at:
        raise HTTPException(status_code=400, detail="Doctor ID and scheduled time are required")
    appointment_data = {
        "patient_id": current_user["sub"],
        "doctor_id": doctor_id,
        "scheduled_at": scheduled_at.isoformat() if isinstance(scheduled_at, datetime) else scheduled_at,
        "status": "pending",
        "notes": data.notes,
    }
    result = supabase_admin.table("appointments").insert(appointment_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to book appointment")
    return result.data[0]

@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(appointment_id: str, update: AppointmentUpdate, current_user: dict = Depends(get_current_user)):
    if not update.model_dump(exclude_unset=True):
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase_admin.table("appointments").update(update.model_dump(exclude_unset=True)).eq("id", appointment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result.data[0]

@router.delete("/{appointment_id}", status_code=204)
def cancel_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    supabase_admin.table("appointments").delete().eq("id", appointment_id).execute()
    return None