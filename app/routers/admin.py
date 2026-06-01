import hashlib, secrets
from fastapi import APIRouter, Depends, Header, HTTPException
from app.database import supabase_admin
from app.middleware.auth import require_role

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users")
def list_users(role: str | None = None, _: dict = Depends(require_role("admin"))):
    query = supabase_admin.table("profiles").select("*")
    if role:
        query = query.eq("role", role)
    return query.order("created_at", desc=True).execute().data or []

@router.get("/stats")
def get_stats(_: dict = Depends(require_role("admin"))):
    patients      = supabase_admin.table("patients").select("id", count="exact").execute()
    doctors       = supabase_admin.table("doctors").select("id", count="exact").execute()
    verified_docs = supabase_admin.table("doctors").select("id", count="exact").eq("is_verified", True).execute()
    active_convs  = supabase_admin.table("conversations").select("id", count="exact").eq("status", "active").execute()
    escalated     = supabase_admin.table("conversations").select("id", count="exact").eq("status", "escalated").execute()
    return {
        "total_patients":          patients.count or 0,
        "total_doctors":           doctors.count or 0,
        "verified_doctors":        verified_docs.count or 0,
        "active_conversations":    active_convs.count or 0,
        "escalated_conversations": escalated.count or 0,
    }

@router.post("/api-keys", status_code=201)
def create_api_key(body: dict, _: dict = Depends(require_role("admin"))):
    """Generate a webhook API key. Returns the plain key ONCE — never stored."""
    plain_key = secrets.token_urlsafe(32)
    key_hash  = hashlib.sha256(plain_key.encode()).hexdigest()
    result = supabase_admin.table("api_keys").insert({
        "name":     body.get("name", "unnamed"),
        "key_hash": key_hash,
    }).execute()
    return {"key": plain_key, "id": result.data[0]["id"], "name": result.data[0]["name"]}

@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(key_id: str, _: dict = Depends(require_role("admin"))):
    supabase_admin.table("api_keys").update({"is_active": False}).eq("id", key_id).execute()
