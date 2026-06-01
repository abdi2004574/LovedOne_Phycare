import socketio
from app.database import is_mock_mode
from app.middleware.auth import decode_token
import time

# Create Socket.IO async server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",   # Tighten in production
    logger=False,
    engineio_logger=False,
)

# In-memory map: sid → {user_id, conv_id, role}
_connections: dict[str, dict] = {}

# Mock message storage
_mock_messages: list[dict] = []

def _get_sukoon_response_new(conversation_id: str, new_message: str) -> tuple[str, bool]:
    """Fallback Sukoon response without Anthropic API."""
    crisis_keywords = ["suicide", "kill myself", "end my life", "want to die", "no reason to live", "self harm"]
    combined = new_message.lower()
    is_crisis = any(kw in combined for kw in crisis_keywords)
    
    reply = "Thank you for sharing. I'm here to listen. How can I help you navigate this feeling today?"
    
    if is_crisis:
        reply = ("I'm very concerned about your safety. Please reach out to Umang Pakistan crisis line immediately: 0311-7786264\n\n" + reply)
    
    return reply, is_crisis

@sio.event
async def connect(sid, environ, auth):
    """
    Client connects with: io(API_URL, { auth: { token, conversation_id } })
    """
    if not auth or "token" not in auth or "conversation_id" not in auth:
        raise ConnectionRefusedError("auth.token and auth.conversation_id required")

    # Validate JWT
    try:
        payload = decode_token(auth["token"])
    except Exception:
        raise ConnectionRefusedError("Invalid token")

    user_id = payload["sub"]
    role    = payload.get("role", "patient")
    conv_id = auth["conversation_id"]

    # Join room and store connection info
    room = f"conv_{conv_id}"
    await sio.enter_room(sid, room)
    _connections[sid] = {"user_id": user_id, "conv_id": conv_id, "role": role, "room": room}

    # Notify others in room
    await sio.emit("user_joined", {"user_id": user_id, "role": role}, room=room, skip_sid=sid)
    print(f"[WS] {role} {user_id} connected to {room}")


@sio.event
async def send_message(sid, data):
    """
    Client emits: socket.emit('send_message', { conversation_id, content })
    """
    conn = _connections.get(sid)
    if not conn:
        return

    conv_id = conn["conv_id"]
    user_id = conn["user_id"]
    role    = conn["role"]
    content = data.get("content", "").strip()

    if not content:
        return

    sender_type = role if role in ("patient", "doctor") else "patient"

    # 1. Save message (mock mode)
    msg = {
        "id": f"m_{int(time.time()*1000)}",
        "conversation_id": conv_id,
        "sender_id": user_id,
        "sender_type": sender_type,
        "content": content,
        "created_at": f"2024-01-15T{int(time.time())%24:02d}:{int(time.time())%60:02d}:00Z",
        "is_read": False,
        "message_type": data.get("message_type", "text"),
    }

    # 2. Broadcast to the entire room (including sender)
    await sio.emit("new_message", msg, room=conn["room"])

    # 3. Get Sukoon's response (mock mode without Anthropic)
    if is_mock_mode():
        try:
            ai_reply, is_crisis = _get_sukoon_response_new(conv_id, content)
        except Exception as e:
            print(f"[AI ERROR] {e}")
            ai_reply = "I'm having trouble responding. Please try again."
            is_crisis = False
    else:
        from app.services.ai_service import get_sukoon_response
        try:
            ai_reply, is_crisis = await get_sukoon_response(conv_id, content)
        except Exception as e:
            print(f"[AI ERROR] {e}")
            ai_reply = "I'm having a little trouble right now. Please try again in a moment."
            is_crisis = False

    # Save AI reply and broadcast
    ai_msg = {
        "id": f"m_{int(time.time()*1000)}_ai",
        "conversation_id": conv_id,
        "sender_id": None,
        "sender_type": "ai",
        "content": ai_reply,
        "created_at": f"2024-01-15T{int(time.time())%24:02d}:{int(time.time())%60:02d}:00Z",
        "is_read": False,
        "message_type": "text",
    }
    await sio.emit("new_message", ai_msg, room=conn["room"])

    # If crisis detected, escalate conversation
    if is_crisis:
        await sio.emit(
            "escalation_alert",
            {"conversation_id": conv_id, "reason": "crisis_detected"},
            room=conn["room"],
        )


@sio.event
async def typing(sid, data):
    """Broadcast typing indicator to room, excluding the sender."""
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
    """Mark all messages in a conversation as read for this user."""
    conn = _connections.get(sid)
    # Mock - no-op


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
