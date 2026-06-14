import socketio
from datetime import datetime, timezone
from app.database import supabase_admin

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

_connections: dict[str, dict] = {}
_room_counts: dict[str, int] = {}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _is_allowed(conv: dict, user_id: str, role: str) -> bool:
    if role == "admin":
        return True
    if role == "patient":
        return conv.get("patient_id") == user_id
    if role == "doctor":
        return conv.get("doctor_id") == user_id or conv.get("type") == "ai"
    return False

def _get_connection_count(room: str) -> int:
    return _room_counts.get(room, 0)

@sio.event
async def connect(sid, environ, auth):
    if not auth or "token" not in auth or "conversation_id" not in auth:
        await sio.emit("error", {"message": "auth.token and auth.conversation_id required"}, to=sid)
        raise ConnectionRefusedError("auth.token and auth.conversation_id required")

    try:
        from app.middleware.auth import decode_token
        payload = decode_token(auth["token"])
    except Exception:
        await sio.emit("error", {"message": "Invalid token"}, to=sid)
        raise ConnectionRefusedError("Invalid token")

    user_id = payload["sub"]
    role = payload.get("role", "patient")
    conv_id = auth["conversation_id"]

    from app.database import supabase_admin
    result = supabase_admin.table("conversations").select("*").eq("id", conv_id).single().execute()
    conv = result.data
    if not conv or not _is_allowed(conv, user_id, role):
        await sio.emit("error", {"message": "Conversation not found or unauthorized"}, to=sid)
        raise ConnectionRefusedError("Conversation not found or unauthorized")

    room = f"conv_{conv_id}"
    await sio.enter_room(sid, room)
    _connections[sid] = {"user_id": user_id, "conv_id": conv_id, "role": role, "room": room}
    _room_counts[room] = _get_connection_count(room) + 1

    messages_result = supabase_admin.table("messages").select("*").eq("conversation_id", conv_id).order("created_at").limit(20).execute()
    history = messages_result.data or []
    await sio.emit("conversation_history", history, to=sid)

    await sio.emit("user_joined", {"user_id": user_id, "role": role}, room=room, skip_sid=sid)
    print(f"[WS] {role} {user_id} connected to {room} (users: {_room_counts[room]})")

@sio.event
async def send_message(sid, data):
    conn = _connections.get(sid)
    if not conn:
        await sio.emit("error", {"message": "Not connected"}, to=sid)
        return

    conv_id = conn["conv_id"]
    user_id = conn["user_id"]
    role = conn["role"]
    content = data.get("content", "").strip()

    if not content:
        return

    from app.database import supabase_admin
    conv_result = supabase_admin.table("conversations").select("*").eq("id", conv_id).single().execute()
    conv = conv_result.data
    if not conv or not _is_allowed(conv, user_id, role):
        await sio.emit("error", {"message": "Not authorized"}, to=sid)
        return

    sender_type = role if role in ("patient", "doctor", "admin") else "patient"
    now = _now()
    message_data = {
        "conversation_id": conv_id,
        "sender_id": user_id,
        "sender_type": sender_type,
        "content": content,
        "message_type": data.get("message_type", "text"),
        "is_read": False,
        "created_at": now,
    }

    result = supabase_admin.table("messages").insert(message_data).execute()
    msg = result.data[0] if result.data else {**message_data, "id": f"m_{now}"}

    await sio.emit("new_message", msg, room=conn["room"])
    supabase_admin.table("conversations").update({"updated_at": now}).eq("id", conv_id).execute()

@sio.event
async def read_receipt(sid, data):
    conn = _connections.get(sid)
    if not conn:
        return
    conv_id = conn["conv_id"]
    user_id = conn["user_id"]
    role = conn["role"]

    result = supabase_admin.table("messages").update({"is_read": True}).eq("conversation_id", conv_id).eq("sender_type", "patient").execute()
    await sio.emit("messages_read", {"conversation_id": conv_id}, room=conn["room"])

@sio.event
async def join_as_doctor(sid, data):
    doctor_id = data.get("doctor_id")
    conv_id = data.get("conversation_id")
    if not doctor_id or not conv_id:
        await sio.emit("error", {"message": "doctor_id and conversation_id required"}, to=sid)
        return

    result = supabase_admin.table("conversations").select("*").eq("id", conv_id).eq("doctor_id", doctor_id).single().execute()
    conv = result.data
    if not conv:
        await sio.emit("error", {"message": "Conversation not found or not assigned to this doctor"}, to=sid)
        return

    room = f"conv_{conv_id}"
    await sio.enter_room(sid, room)
    _connections[sid] = {"user_id": doctor_id, "conv_id": conv_id, "role": "doctor", "room": room}
    _room_counts[room] = _get_connection_count(room) + 1

    messages_result = supabase_admin.table("messages").select("*").eq("conversation_id", conv_id).order("created_at").limit(20).execute()
    history = messages_result.data or []
    await sio.emit("conversation_history", history, to=sid)
    print(f"[WS] doctor {doctor_id} joined {room} (users: {_room_counts[room]})")

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
    supabase_admin.table("messages").update({"is_read": True}).eq("conversation_id", conn["conv_id"]).eq("sender_id", conn["user_id"]).execute()

@sio.event
async def disconnect(sid):
    conn = _connections.pop(sid, None)
    if conn:
        room = conn["room"]
        _room_counts[room] = max(0, _room_counts.get(room, 1) - 1)
        await sio.emit(
            "user_left",
            {"user_id": conn["user_id"]},
            room=room,
        )
        print(f"[WS] {conn['role']} {conn['user_id']} disconnected from {room} (users: {_room_counts[room]})")