"""Schémas Pydantic — Loyalty Engine Sprint 2"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── LoyaltyProgram ─────────────────────────────────────────────────────────────

class CreateProgramRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    points_per_xof: float = Field(0.01, gt=0, description="Points par XOF dépensé")
    min_spend_xof: int = Field(0, ge=0)
    expiry_months: Optional[int] = Field(None, ge=1)


class UpdateProgramRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    points_per_xof: Optional[float] = Field(None, gt=0)
    min_spend_xof: Optional[int] = Field(None, ge=0)
    expiry_months: Optional[int] = Field(None, ge=1)


class ProgramResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    description: Optional[str]
    loyalty_enabled: bool
    points_per_xof: float
    min_spend_xof: int
    expiry_months: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── LoyaltyTier ────────────────────────────────────────────────────────────────

class CreateTierRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    min_points: int = Field(0, ge=0)
    multiplier: float = Field(1.0, gt=0)
    benefits: Optional[dict] = None
    sort_order: int = Field(0, ge=0)


class TierResponse(BaseModel):
    id: UUID
    program_id: UUID
    company_id: UUID
    name: str
    min_points: int
    multiplier: float
    benefits: Optional[dict]
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── CardTemplate ───────────────────────────────────────────────────────────────

class CreateCardTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    tier_id: Optional[UUID] = None
    background_color: str = Field("#1A1A2E", pattern=r"^#[0-9A-Fa-f]{6}$")
    text_color: str = Field("#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: Optional[str] = None
    background_image_url: Optional[str] = None
    is_default: bool = False


class CardTemplateResponse(BaseModel):
    id: UUID
    company_id: UUID
    tier_id: Optional[UUID]
    name: str
    background_color: str
    text_color: str
    logo_url: Optional[str]
    background_image_url: Optional[str]
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── LoyaltyCard ────────────────────────────────────────────────────────────────

class IssueNativeCardRequest(BaseModel):
    """Émettre une carte native (programme du commerçant)."""
    customer_id: UUID
    program_id: UUID
    card_template_id: Optional[UUID] = None


class ImportExternalCardRequest(BaseModel):
    """Importer une carte externe (ex : carte d'un autre enseigne)."""
    customer_id: UUID
    external_issuer: str = Field(..., min_length=1, max_length=120)
    external_ref: str = Field(..., min_length=1, max_length=120)
    card_template_id: Optional[UUID] = None


class LoyaltyCardResponse(BaseModel):
    id: UUID
    company_id: UUID
    customer_id: UUID
    program_id: Optional[UUID]
    tier_id: Optional[UUID]
    card_template_id: Optional[UUID]
    card_number: str
    points_balance: int
    card_type: str
    external_issuer: Optional[str]
    external_ref: Optional[str] = None
    status: str
    issued_at: datetime
    expires_at: Optional[datetime]
    # Champs enrichis pour l'affichage frontend
    company_name: Optional[str] = None
    program_name: Optional[str] = None
    tier_name: Optional[str] = None
    background_color: Optional[str] = "#1A1A2E"
    text_color: Optional[str] = "#FFFFFF"
    logo_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ── LoyaltyTransaction ─────────────────────────────────────────────────────────

class EarnPointsRequest(BaseModel):
    card_id: UUID
    order_id: Optional[UUID] = None
    amount_xof: int = Field(..., gt=0, description="Montant de la commande en XOF")
    description: Optional[str] = None


class RedeemPointsRequest(BaseModel):
    card_id: UUID
    points: int = Field(..., gt=0)
    order_id: Optional[UUID] = None
    description: Optional[str] = None


class LoyaltyTransactionResponse(BaseModel):
    id: UUID
    company_id: UUID
    card_id: UUID
    customer_id: UUID
    order_id: Optional[UUID]
    type: str
    points_delta: int
    points_before: int
    points_after: int
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── LoyaltyReward ──────────────────────────────────────────────────────────────

class CreateRewardRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    points_cost: int = Field(..., gt=0)
    reward_type: str = Field(..., pattern=r"^(discount_pct|discount_fixed|free_product|gift)$")
    value: float = Field(0, ge=0)
    max_redemptions: Optional[int] = Field(None, ge=1)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class RewardResponse(BaseModel):
    id: UUID
    company_id: UUID
    program_id: UUID
    name: str
    description: Optional[str]
    points_cost: int
    reward_type: str
    value: float
    max_redemptions: Optional[int]
    redemptions_count: int
    is_active: bool
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── LoyaltyCoupon ──────────────────────────────────────────────────────────────

class IssueCouponRequest(BaseModel):
    customer_id: UUID
    reward_id: Optional[UUID] = None
    discount_type: str = Field(..., pattern=r"^(pct|fixed)$")
    discount_value: float = Field(..., gt=0)
    min_order_xof: int = Field(0, ge=0)
    expires_at: Optional[datetime] = None


class CouponResponse(BaseModel):
    id: UUID
    company_id: UUID
    customer_id: UUID
    reward_id: Optional[UUID]
    code: str
    discount_type: str
    discount_value: float
    min_order_xof: int
    is_used: bool
    used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── CustomerScore / Intelligence (Sprint 5) ────────────────────────────────────

class CustomerScoreResponse(BaseModel):
    id: UUID
    company_id: UUID
    customer_id: UUID
    recency_score: int
    frequency_score: int
    monetary_score: int
    rfm_score: int
    segment: str
    last_order_date: Optional[datetime]
    order_count: int
    total_spent_xof: int
    computed_at: datetime

    model_config = {"from_attributes": True}


class CustomerProfileResponse(BaseModel):
    customer_id: UUID
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    score: Optional[CustomerScoreResponse]
    cards: list[LoyaltyCardResponse]
    total_spent_xof: int
    order_count: int
    segment: Optional[str]

    model_config = {"from_attributes": True}
