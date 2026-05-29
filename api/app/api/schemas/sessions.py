from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: str
    template_name: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class SessionCreateResponse(BaseModel):
    id: str
    template_name: str
    created_at: datetime
