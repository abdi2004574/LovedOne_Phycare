from fastapi import APIRouter, Depends, HTTPException, status
from Backend.database import supabase
from Backend.middleware.auth import get_current_user

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.get("/conversations/{conversation_id}")
def get_messages(conversation_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
    return result.data

@router.post("/conversations/{conversation_id}")
def send_message(conversation_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    content = data.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Message content is required")
    message_data = {
        "conversation_id": conversation_id,
        "sender_id": current_user["sub"],
        "sender_type": current_user["role"],
        "content": content,
        "message_type": data.get("message_type", "text"),
    }
    result = supabase.table("messages").insert(message_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to send message")
    supabase.table("conversations").update({"updated_at": "now()"}).eq("id", conversation_id).execute()
    return result.data[0]
