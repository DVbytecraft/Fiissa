from typing import Optional
from pydantic import BaseModel


class SuspendToggleRequest(BaseModel):
    suspend: bool
    reason: Optional[str] = None


class PlatformStatsResponse(BaseModel):
    total_companies: int
    active_companies: int
    total_users: int
    orders_this_month: int
    revenue_xof: int
    active_subscriptions: int


class CompanyAdminResponse(BaseModel):
    id: str
    name: str
    type: str
    country: str
    is_active: bool
    slug: Optional[str] = None
    contact_email: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: str
