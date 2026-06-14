from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel

ConvType   = Literal["ai", "human", "hybrid"]
ConvStatus = Literal["active", "closed", "escalated"]
SenderType = Literal["patient", "doctor", "ai"]

class ConversationCreate(BaseModel):
    type: ConvType = "ai"

class ConversationResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: Optional[str] = None
    type: ConvType
    status: ConvStatus
    created_at: str

class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: Optional[str] = None
    sender_type: SenderType
    content: str
    message_type: str
    is_read: bool
    created_at: str
    sender_name: Optional[str] = None
    sender_avatar: Optional[str] = None

class EscalateRequest(BaseModel):
    doctor_id: str