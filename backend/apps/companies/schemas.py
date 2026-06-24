from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class CompanyCreate(BaseModel):
    name: str
    type: str
    country: str = "SN"
    currency: str = "XOF"
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[dict] = None


class CompanySettingsUpdate(BaseModel):
    currency: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    catalog_mode: Optional[str] = None
    payment_mode: Optional[str] = None
    delivery_mode: Optional[str] = None
    vat_rate: Optional[Decimal] = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    type: str
    country: str
    currency: str
    is_active: bool
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: str
    plan: str
    status: str
    started_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_trial: bool = False
