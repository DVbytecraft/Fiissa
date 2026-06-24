from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class TicketCreate(BaseModel):
    subject: str
    body: str
    priority: str = "medium"
    category: Optional[str] = None


class MessageCreate(BaseModel):
    body: str
    is_internal: bool = False


class TicketResponse(BaseModel):
    id: str
    company_id: str
    subject: str
    status: str
    priority: str
    category: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    ticket_id: str
    body: str
    is_internal: bool
    created_at: str

    class Config:
        from_attributes = True
