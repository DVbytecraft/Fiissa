from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: str
    last_name: str
    full_name: str
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class StaffInviteRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    store_id: Optional[UUID] = None
    send_email: bool = True


class StaffRoleResponse(BaseModel):
    id: str
    email: Optional[str] = None
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: str
