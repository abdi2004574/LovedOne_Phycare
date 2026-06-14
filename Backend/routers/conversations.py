from fastapi import APIRouter, Depends, HTTPException, status
from Backend.database import supabase
from Backend.middleware.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("/")
def get_conversations(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    role = current_user["role"]
    if role == "patient":
        result = supabase.table("conversations").select("*").eq("patient_id", user_id).order("updated_at", desc=True).execute()
    elif role == "doctor":
        result = supabase.table("conversations").select("*").eq("doctor_id", user_id).order("updated_at", desc=True).execute()
    elif role == "admin":
        result = supabase.table("conversations").select("*").order("updated_at", desc=True).execute()
    else:
        raise HTTPException(status_code=403, detail="Invalid role")
    return result.data

@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("conversations").select("*").eq("id", conversation_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv = result.data
    user_id = current_user["sub"]
    role = current_user["role"]
    if role == "patient" and conv["patient_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if role == "doctor" and conv.get("doctor_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return conv

@router.post("/")
def create_conversation(data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only patients can create conversations")
    conversation_data = {
        "patient_id": current_user["sub"],
        "type": data.get("type", "ai"),
        "status": "active",
        "title": data.get("title") or "New Conversation",
    }
    result = supabase.table("conversations").insert(conversation_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create conversation")
    return result.data[0]

@router.patch("/{conversation_id}")
def update_conversation(conversation_id: str, update: dict, current_user: dict = Depends(get_current_user)):
    if not update:
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase.table("conversations").update(update).eq("id", conversation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]

@router.post("/{conversation_id}/escalate")
def escalate_conversation(conversation_id: str, doctor_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("conversations").update({"type": "human", "doctor_id": doctor_id, "status": "active"}).eq("id", conversation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]

@router.post("/{conversation_id}/close")
def close_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("conversations").update({"status": "closed"}).eq("id", conversation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]
