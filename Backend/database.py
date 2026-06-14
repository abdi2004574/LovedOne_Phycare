from supabase import create_client

from Backend.config import settings


supabase = create_client(settings.supabase_url, settings.supabase_key)
supabase_admin = create_client(settings.supabase_url, settings.supabase_service_key)


def get_supabase():
    return supabase


def get_supabase_admin():
    return supabase_admin


def is_mock_mode() -> bool:
    return False
