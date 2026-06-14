from fastapi import APIRouter, Depends, HTTPException, status
from Backend.database import supabase
from Backend.middleware.auth import get_current_patient, get_current_user

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.get("/")
def get_appointments(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    role = current_user["role"]
    if role == "patient":
        result = supabase.table("appointments").select("*").eq("patient_id", user_id).order("scheduled_at").execute()
    elif role == "doctor":
        result = supabase.table("appointments").select("*").eq("doctor_id", user_id).order("scheduled_at").execute()
    else:
        result = supabase.table("appointments").select("*").order("scheduled_at").execute()
    return result.data

@router.post("/")
def create_appointment(data: dict, current_user: dict = Depends(get_current_patient)):
    if current_user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only patients can book appointments")
    doctor_id = data.get("doctor_id")
    scheduled_at = data.get("scheduled_at")
    if not doctor_id or not scheduled_at:
        raise HTTPException(status_code=400, detail="Doctor ID and scheduled time are required")
    appointment_data = {
        "patient_id": current_user["sub"],
        "doctor_id": doctor_id,
        "scheduled_at": scheduled_at,
        "status": "pending",
        "notes": data.get("notes"),
    }
    result = supabase.table("appointments").insert(appointment_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to book appointment")
    return result.data[0]

@router.patch("/{appointment_id}")
def update_appointment(appointment_id: str, update: dict, current_user: dict = Depends(get_current_user)):
    if not update:
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase.table("appointments").update(update).eq("id", appointment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result.data[0]
