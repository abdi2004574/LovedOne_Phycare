import hashlib
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from app.database import supabase_admin

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

async def verify_api_key(x_api_key: str = Header(...)):
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    result = supabase_admin.table("api_keys").select("*").eq("key_hash", key_hash).eq("is_active", True).execute()
    if not result.data:
        raise HTTPException(403, "Invalid or revoked API key")
    return result.data[0]

@router.post("/supabase")
async def supabase_webhook(request: Request, api_key: dict = Depends(verify_api_key)):
    payload = await request.json()
    table  = payload.get("table")
    event  = payload.get("type")
    record = payload.get("record", {})

    if table == "messages" and event == "INSERT":
        print(f"New message in conv {record.get('conversation_id')}")

    if table == "conversations" and event == "UPDATE":
        if record.get("status") == "escalated":
            print(f"Conversation {record.get('id')} escalated — notify doctors")

    return {"received": True}

@router.post("/payment")
async def payment_webhook(request: Request, api_key: dict = Depends(verify_api_key)):
    payload = await request.json()
    print(f"Payment event received: {payload}")
    return {"received": True}