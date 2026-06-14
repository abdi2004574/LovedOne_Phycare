from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import supabase, supabase_admin
from app.middleware.auth import get_current_user
from app.schemas.conversation import MessageResponse

router = APIRouter(prefix="/conversations", tags=["Messages"])

@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(conversation_id: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    result = supabase_admin.table("messages").select("*, profiles(full_name, avatar_url)").eq("conversation_id", conversation_id).order("created_at").range((page-1)*page_size, page*page_size - 1).execute()
    messages = []
    for msg in (result.data or []):
        messages.append({
            **msg,
            "sender_name": msg.get("profiles", {}).get("full_name") if msg.get("profiles") else None,
            "sender_avatar": msg.get("profiles", {}).get("avatar_url") if msg.get("profiles") else None,
        })
    return messages

@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
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
        "is_read": False,
    }
    result = supabase_admin.table("messages").insert(message_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to send message")
    supabase_admin.table("conversations").update({"updated_at": "now()"}).eq("id", conversation_id).execute()
    return result.data[0]