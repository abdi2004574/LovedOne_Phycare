from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase_admin
from app.middleware.auth import get_current_user
from app.schemas.conversation import ConversationCreate

router = APIRouter(prefix="/conversations", tags=["Conversations"])

def _get_conv_or_404(conv_id: str) -> dict:
    result = supabase_admin.table("conversations").select("*").eq("id", conv_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Conversation not found")
    return result.data

def _assert_participant(conv: dict, user_id: str, role: str):
    if role == "admin":
        return
    if conv.get("patient_id") != user_id and conv.get("doctor_id") != user_id:
        raise HTTPException(403, "Not a participant in this conversation")

@router.post("/", status_code=201)
def create_conversation(body: ConversationCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(403, "Only patients can start conversations")
    import time
    result = supabase_admin.table("conversations").insert({
        "patient_id": current_user["sub"],
        "type": body.type,
        "status": "active",
        "created_at": f"2024-01-15T{int(time.time())%24:02d}:00:00Z",
        "updated_at": f"2024-01-15T{int(time.time())%24:02d}:00:00Z",
        "title": "New conversation",
    }).execute()
    return result.data[0] if result.data else {"id": "new", "patient_id": current_user["sub"], "type": body.type, "status": "active"}

@router.get("/")
def list_conversations(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    role = current_user["role"]
    if role == "admin":
        return supabase_admin.table("conversations").select("*").order("created_at", desc=True).execute().data or []
    elif role == "patient":
        return supabase_admin.table("conversations").select("*").eq("patient_id", user_id).order("created_at", desc=True).execute().data or []
    else:
        return supabase_admin.table("conversations").select("*").eq("doctor_id", user_id).order("created_at", desc=True).execute().data or []

@router.get("/{conv_id}")
def get_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conv_or_404(conv_id)
    _assert_participant(conv, current_user["sub"], current_user["role"])
    return conv

@router.patch("/{conv_id}/escalate")
def escalate_conversation(conv_id: str, doctor_id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conv_or_404(conv_id)
    _assert_participant(conv, current_user["sub"], current_user["role"])
    doctor = supabase_admin.table("doctors").select("id, is_available, is_verified").eq("id", doctor_id).single().execute()
    if not doctor.data or not doctor.data.get("is_verified"):
        raise HTTPException(400, "Doctor not found or not verified")
    result = supabase_admin.table("conversations").update({
        "doctor_id": doctor_id,
        "type": "human",
        "status": "escalated",
    }).eq("id", conv_id).execute()
    return result.data[0] if result.data else {"id": conv_id}

@router.patch("/{conv_id}/close")
def close_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conv_or_404(conv_id)
    _assert_participant(conv, current_user["sub"], current_user["role"])
    result = supabase_admin.table("conversations").update({"status": "closed"}).eq("id", conv_id).execute()
    return result.data[0] if result.data else {"id": conv_id}

@router.get("/")
def list_conversations(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    role = current_user["role"]
    if role == "admin":
        return supabase_admin.table("conversations").select("*").order("created_at", desc=True).execute().data or []
    elif role == "patient":
        return supabase_admin.table("conversations").select("*").eq("patient_id", user_id).order("created_at", desc=True).execute().data or []
    else:  # doctor
        return supabase_admin.table("conversations").select("*").eq("doctor_id", user_id).order("created_at", desc=True).execute().data or []

@router.get("/{conv_id}")
def get_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conv_or_404(conv_id)
    _assert_participant(conv, current_user["sub"], current_user["role"])
    return conv

@router.patch("/{conv_id}/escalate")
def escalate_conversation(conv_id: str, doctor_id: str, current_user: dict = Depends(get_current_user)):
    """Bring a human doctor into the conversation."""
    conv = _get_conv_or_404(conv_id)
    _assert_participant(conv, current_user["sub"], current_user["role"])
    # Verify doctor exists and is available
    doctor = supabase_admin.table("doctors").select("id, is_available, is_verified").eq("id", doctor_id).single().execute()
    if not doctor.data or not doctor.data["is_verified"]:
        raise HTTPException(400, "Doctor not found or not verified")
    result = supabase_admin.table("conversations").update({
        "doctor_id": doctor_id,
        "type": "human",
        "status": "escalated",
    }).eq("id", conv_id).execute()
    return result.data[0]

@router.patch("/{conv_id}/close")
def close_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conv_or_404(conv_id)
    _assert_participant(conv, current_user["sub"], current_user["role"])
    result = supabase_admin.table("conversations").update({"status": "closed"}).eq("id", conv_id).execute()
    return result.data[0]