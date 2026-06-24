from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class StoreCreate(BaseModel):
    company_id: UUID
    name: str
    description: Optional[str] = None
    address: Optional[dict] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None
    scan_go_enabled: bool = False
    delivery_enabled: bool = True
    click_collect_enabled: bool = True
    mobile_money_info: Optional[dict] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[dict] = None
    phone: Optional[str] = None
    opening_hours: Optional[dict] = None
    mobile_money_info: Optional[dict] = None
    scan_go_enabled: Optional[bool] = None
    delivery_enabled: Optional[bool] = None
    click_collect_enabled: Optional[bool] = None
    delivery_fee_xof: Optional[int] = None
    is_active: Optional[bool] = None


class StoreResponse(BaseModel):
    id: str
    company_id: str
    name: str
    description: Optional[str] = None
    address: Optional[dict] = None
    phone: Optional[str] = None
    click_collect_enabled: bool
    delivery_enabled: bool
    scan_go_enabled: bool
    delivery_fee_xof: int
    is_active: bool

    class Config:
        from_attributes = True
