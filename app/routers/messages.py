from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase_admin
from app.middleware.auth import get_current_user
from app.schemas.conversation import MessageCreate
import time

router = APIRouter(prefix="/conversations", tags=["Messages"])

@router.get("/{conv_id}/messages")
def get_messages(conv_id: str, current_user: dict = Depends(get_current_user), limit: int = 50, offset: int = 0):
    if supabase_admin.table("conversations").select("*").eq("id", conv_id).single().execute().data is None:
        raise HTTPException(404, "Conversation not found")
    result = (
        supabase_admin.table("messages")
        .select("*")
        .eq("conversation_id", conv_id)
        .order("created_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or []

@router.post("/{conv_id}/messages", status_code=201)
def send_message(conv_id: str, body: MessageCreate, current_user: dict = Depends(get_current_user)):
    """REST fallback — prefer WebSocket for real-time chat."""
    if supabase_admin.table("conversations").select("*").eq("id", conv_id).single().execute().data is None:
        raise HTTPException(404, "Conversation not found")
    uid, role = current_user["sub"], current_user["role"]
    sender_type = role if role in ("patient", "doctor") else "patient"
    result = supabase_admin.table("messages").insert({
        "conversation_id": conv_id,
        "sender_id": uid,
        "sender_type": sender_type,
        "content": body.content,
        "message_type": body.message_type or "text",
        "is_read": False,
        "created_at": f"2024-01-15T{int(time.time())%24:02d}:{int(time.time())%60:02d}:00Z",
    }).execute()
    return result.data[0] if result.data else {"id": "new", "conversation_id": conv_id}
