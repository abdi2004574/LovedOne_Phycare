from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


ConvType = Literal["ai", "human", "hybrid"]
ConvStatus = Literal["active", "closed", "escalated"]
SenderType = Literal["patient", "doctor", "ai", "admin", "system"]


class ConversationCreate(BaseModel):
    type: ConvType = "ai"
    title: Optional[str] = None


class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"
