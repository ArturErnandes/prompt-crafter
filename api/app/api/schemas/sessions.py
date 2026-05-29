from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: UUID
    template_name: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class SessionCreateResponse(BaseModel):
    id: UUID
    template_name: str
    created_at: datetime
