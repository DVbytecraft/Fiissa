from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    company_id: str
    user_id: str
    title: str
    body: str
    type: str  # "order_update" | "payment_confirmed" | "payment_rejected" | "order_ready" | "system"
    is_read: bool
    read_at: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: str
    company_id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    old_data: Optional[dict] = None
    new_data: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True
