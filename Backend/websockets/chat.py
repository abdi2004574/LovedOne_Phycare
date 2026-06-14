import socketio
from datetime import datetime, timezone

from Backend.config import settings
from Backend.database import supabase
from Backend.middleware.auth import decode_token

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

_connections: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_allowed(conv: dict, user_id: str, role: str) -> bool:
    if role == "admin":
        return True
    if role == "patient":
        return conv.get("patient_id") == user_id
    if role == "doctor":
        return conv.get("doctor_id") == user_id
    return False


@sio.event
async def connect(sid, environ, auth):
    if not auth or "token" not in auth or "conversation_id" not in auth:
        raise ConnectionRefusedError("auth.token and auth.conversation_id required")

    try:
        payload = decode_token(auth["token"])
    except Exception:
        raise ConnectionRefusedError("Invalid token")

    user_id = payload["sub"]
    role = payload.get("role", "patient")
    conv_id = auth["conversation_id"]

    result = supabase.table("conversations").select("*").eq("id", conv_id).single().execute()
    conv = result.data
    if not conv or not _is_allowed(conv, user_id, role):
        raise ConnectionRefusedError("Conversation not found or unauthorized")

    room = f"conv_{conv_id}"
    await sio.enter_room(sid, room)
    _connections[sid] = {"user_id": user_id, "conv_id": conv_id, "role": role, "room": room}

    await sio.emit("user_joined", {"user_id": user_id, "role": role}, room=room, skip_sid=sid)
    print(f"[WS] {role} {user_id} connected to {room}")


@sio.event
async def send_message(sid, data):
    conn = _connections.get(sid)
    if not conn:
        return

    conv_id = conn["conv_id"]
    user_id = conn["user_id"]
    role = conn["role"]
    content = data.get("content", "").strip()

    if not content:
        return

    conv_result = supabase.table("conversations").select("*").eq("id", conv_id).single().execute()
    conv = conv_result.data
    if not conv or not _is_allowed(conv, user_id, role):
        return

    sender_type = role if role in ("patient", "doctor", "admin") else "patient"
    now = _now()
    message_data = {
        "conversation_id": conv_id,
        "sender_id": user_id,
        "sender_type": sender_type,
        "content": content,
        "message_type": data.get("message_type", "text"),
        "created_at": now,
    }

    result = supabase.table("messages").insert(message_data).execute()
    msg = result.data[0] if result.data else {**message_data, "id": f"m_{now}"}

    await sio.emit("new_message", msg, room=conn["room"])
    supabase.table("conversations").update({"updated_at": now}).eq("id", conv_id).execute()

    if conv.get("type") == "ai":
        try:
            if settings.anthropic_api_key:
                from Backend.services.ai_service import get_sukoon_response
                ai_reply, is_crisis = await get_sukoon_response(conv_id, content)
            else:
                ai_reply = "AI responses are not configured for this server."
                is_crisis = False
        except Exception as e:
            print(f"[AI ERROR] {e}")
            ai_reply = "I'm having trouble responding. Please try again."
            is_crisis = False

        ai_msg = {
            "conversation_id": conv_id,
            "sender_id": None,
            "sender_type": "ai",
            "content": ai_reply,
            "message_type": "text",
            "created_at": _now(),
        }
        ai_result = supabase.table("messages").insert(ai_msg).execute()
        ai_msg = ai_result.data[0] if ai_result.data else {**ai_msg, "id": f"m_ai_{now}"}
        await sio.emit("new_message", ai_msg, room=conn["room"])
        if is_crisis:
            supabase.table("conversations").update({"type": "human", "status": "escalated"}).eq("id", conv_id).execute()
            await sio.emit(
                "escalation_alert",
                {"conversation_id": conv_id, "reason": "crisis_detected"},
                room=conn["room"],
            )


@sio.event
async def typing(sid, data):
    conn = _connections.get(sid)
    if conn:
        await sio.emit(
            "user_typing",
            {"user_id": conn["user_id"], "role": conn["role"]},
            room=conn["room"],
            skip_sid=sid,
        )


@sio.event
async def mark_read(sid, data):
    conn = _connections.get(sid)
    if not conn:
        return
    supabase.table("messages").update({"is_read": True}).eq("conversation_id", conn["conv_id"]).eq("sender_id", conn["user_id"]).execute()


@sio.event
async def disconnect(sid):
    conn = _connections.pop(sid, None)
    if conn:
        await sio.emit(
            "user_left",
            {"user_id": conn["user_id"]},
            room=conn["room"],
        )
        print(f"[WS] {conn['role']} {conn['user_id']} disconnected")
