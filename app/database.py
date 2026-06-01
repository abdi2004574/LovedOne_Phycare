"""Mock database layer for development without Supabase."""
import time
from typing import Any

# In-memory mock database shared across all modules
_mock_db: dict[str, list[dict]] = {
    "profiles": [
        {"id": "acc_admin", "full_name": "Platform Admin", "phone": None, "role": "admin", "language": "en"},
        {"id": "acc_th_sarah", "full_name": "Dr. Sarah Ahmed", "phone": "+92-300-1234567", "role": "doctor", "language": "en"},
        {"id": "acc_th_omar", "full_name": "Dr. Omar Khan", "phone": "+92-300-7654321", "role": "doctor", "language": "en"},
        {"id": "acc_user_demo", "full_name": "Ayesha Demo", "phone": None, "role": "patient", "language": "en"},
    ],
    "patients": [
        {"id": "acc_user_demo"},
    ],
    "doctors": [
        {"id": "acc_th_sarah", "pmdc_number": "12345", "specialization": "Clinical Psychology", "bio": "10+ years experience", "is_verified": True, "is_available": True},
        {"id": "acc_th_omar", "pmdc_number": "67890", "specialization": "Counseling", "bio": "5+ years experience", "is_verified": False, "is_available": False},
    ],
    "conversations": [
        {"id": "conv_demo", "patient_id": "acc_user_demo", "doctor_id": None, "type": "ai", "status": "active", "created_at": "2024-01-15T10:00:00Z", "updated_at": "2024-01-15T10:00:00Z", "title": "Your conversation"},
    ],
    "messages": [
        {"id": "m_welcome", "conversation_id": "conv_demo", "sender_id": None, "sender_type": "system", "content": "Welcome to LovedOne PsyCare. This is a safe space.", "created_at": "2024-01-15T10:00:00Z", "is_read": True, "message_type": "text"},
    ],
}

class MockTable:
    """Mock table that mimics Supabase table API."""
    def __init__(self, name: str):
        self.name = name
        self._filters: list[tuple[str, str, Any]] = []
        self._order_field: str | None = None
        self._order_desc = False
        self._single = False
        
    def select(self, fields: str = "*"):
        self._filters = []
        self._single = False
        return self
    
    def eq(self, field: str, value: Any):
        self._filters.append(("eq", field, value))
        return self
    
    def neq(self, field: str, value: Any):
        self._filters.append(("neq", field, value))
        return self
    
    def order(self, field: str, desc: bool = False):
        self._order_field = field
        self._order_desc = desc
        return self
    
    def single(self):
        self._single = True
        return self
    
    def limit(self, count: int):
        return self
    
    def range(self, start: int, end: int):
        return self
    
    def insert(self, data: dict | list[dict]):
        if isinstance(data, dict):
            data = [data]
        results = []
        for item in data:
            if "id" not in item:
                item["id"] = f"{self.name[:3]}_{int(time.time()*1000000)}"
            _mock_db[self.name].append(item.copy())
            results.append(item)
        return MockResult(results[0] if len(results) == 1 else results)
    
    def update(self, data: dict):
        for table_item in _mock_db[self.name]:
            matches = all(table_item.get(f) == v for _, f, v in self._filters)
            if matches:
                table_item.update(data)
                return MockResult(table_item)
        return MockResult(None)
    
    def delete(self):
        for table_item in _mock_db[self.name][:]:
            matches = all(table_item.get(f) == v for _, f, v in self._filters)
            if matches:
                _mock_db[self.name].remove(table_item)
                return MockResult(None)
        return MockResult(None)
    
    def execute(self) -> "MockResult":
        return MockResult(self._fetch())
    
    def _fetch(self) -> list[dict] | dict | None:
        items = _mock_db.get(self.name, [])
        
        # Apply filters
        for op, field, value in self._filters:
            if op == "eq":
                items = [i for i in items if i.get(field) == value]
            elif op == "neq":
                items = [i for i in items if i.get(field) != value]
        
        # Handle single()
        if self._single:
            if items:
                return items[0]
            return None
        
        return items


class MockResult:
    def __init__(self, data: Any):
        self.data = data


class MockSupabaseClient:
    def table(self, name: str) -> MockTable:
        return MockTable(name)


# Create mock clients
supabase = MockSupabaseClient()
supabase_admin = MockSupabaseClient()


def get_supabase() -> MockSupabaseClient:
    return supabase


def get_supabase_admin() -> MockSupabaseClient:
    return supabase_admin


def is_mock_mode() -> bool:
    return True