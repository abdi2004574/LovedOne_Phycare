from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
supabase_admin: Client = create_client(settings.supabase_url, settings.supabase_service_key)

def get_supabase() -> Client:
    return supabase

def get_supabase_admin() -> Client:
    return supabase_admin

def is_mock_mode() -> bool:
    return settings.is_dev

def table(name: str, admin: bool = False):
    client = supabase_admin if admin else supabase
    return client.table(name)