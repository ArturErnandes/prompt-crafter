from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime
