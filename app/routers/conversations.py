from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import supabase, supabase_admin
from app.middleware.auth import get_current_user
from app.schemas.conversation import ConversationCreate, ConversationResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("/", response_model=list[ConversationResponse])
def get_conversations(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    role = current_user["role"]
    if role == "patient":
        result = supabase_admin.table("conversations").select("*").eq("patient_id", user_id).order("updated_at", desc=True).range((page-1)*page_size, page*page_size - 1).execute()
    elif role == "doctor":
        result = supabase_admin.table("conversations").select("*").eq("doctor_id", user_id).order("updated_at", desc=True).range((page-1)*page_size, page*page_size - 1).execute()
    elif role == "admin":
        result = supabase_admin.table("conversations").select("*").order("updated_at", desc=True).range((page-1)*page_size, page*page_size - 1).execute()
    else:
        raise HTTPException(status_code=403, detail="Invalid role")
    return result.data or []

@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase_admin.table("conversations").select("*").eq("id", conversation_id).single().execute()
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

@router.post("/", response_model=ConversationResponse, status_code=201)
def create_conversation(data: ConversationCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only patients can create conversations")
    conversation_data = {
        "patient_id": current_user["sub"],
        "type": data.type,
        "status": "active",
    }
    result = supabase_admin.table("conversations").insert(conversation_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create conversation")
    return result.data[0]

@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(conversation_id: str, update: dict, current_user: dict = Depends(get_current_user)):
    if not update:
        raise HTTPException(status_code=400, detail="No update data provided")
    result = supabase_admin.table("conversations").update(update).eq("id", conversation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]

@router.patch("/{conversation_id}/escalate", response_model=ConversationResponse)
def escalate_conversation(conversation_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    doctor_id = body.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=400, detail="doctor_id is required")
    result = supabase_admin.table("conversations").update({"type": "human", "doctor_id": doctor_id, "status": "active"}).eq("id", conversation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]

@router.patch("/{conversation_id}/close", response_model=ConversationResponse)
def close_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase_admin.table("conversations").update({"status": "closed"}).eq("id", conversation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]