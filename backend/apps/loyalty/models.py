"""
Modèles Loyalty Engine — Sprint 2

Tables :
  loyalty_programs    — Programme fidélité d'un commerçant (loyalty_enabled=False par défaut)
  loyalty_tiers       — Niveaux dans un programme (bronze, silver, gold…)
  card_templates      — Design visuel d'une carte virtuelle
  loyalty_cards       — Carte d'un client (native ou externe)
  loyalty_transactions — Ledger append-only des mouvements de points
  loyalty_rewards     — Récompenses disponibles dans un programme
  loyalty_coupons     — Coupons émis pour un client
  customer_scores     — Score RFM par (company, customer)

Règles absolues :
  - Fiissa ne crée JAMAIS automatiquement un programme ou une carte fidélité.
  - loyalty_enabled = False par défaut.
  - points_balance est une valeur commerciale définie par le marchand, JAMAIS un solde monétaire Fiissa.
  - loyalty_transactions est append-only : aucun update/delete permis.
  - Multi-tenant : company_id présent sur toutes les tables.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

CARD_TYPE_VALUES = ("native", "external")
CARD_STATUS_VALUES = ("active", "suspended", "cancelled")
TRANSACTION_TYPE_VALUES = ("earn", "redeem", "bonus", "expire", "adjust")
REWARD_TYPE_VALUES = ("discount_pct", "discount_fixed", "free_product", "gift")
DISCOUNT_TYPE_VALUES = ("pct", "fixed")
SEGMENT_VALUES = ("new", "active", "loyal", "vip", "at_risk", "inactive")


# ── loyalty_programs ───────────────────────────────────────────────────────────

class LoyaltyProgram(Base, TimestampMixin):
    """
    Programme fidélité d'un commerçant.
    Règle : loyalty_enabled = False par défaut. Fiissa ne crée jamais ce programme automatiquement.
    """
    __tablename__ = "loyalty_programs"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_loyalty_program_company_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    loyalty_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    points_per_xof: Mapped[float] = mapped_column(
        Numeric(10, 4), nullable=False, default=0.01,
        comment="Points gagnés par XOF dépensé. Ex: 0.01 = 1 point pour 100 XOF."
    )
    min_spend_xof: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expiry_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    tiers: Mapped[list["LoyaltyTier"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="LoyaltyTier.min_points"
    )
    rewards: Mapped[list["LoyaltyReward"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    cards: Mapped[list["LoyaltyCard"]] = relationship(back_populates="program")


# ── loyalty_tiers ──────────────────────────────────────────────────────────────

class LoyaltyTier(Base, TimestampMixin):
    __tablename__ = "loyalty_tiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    min_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    multiplier: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)
    benefits: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    program: Mapped["LoyaltyProgram"] = relationship(back_populates="tiers")
    templates: Mapped[list["CardTemplate"]] = relationship(back_populates="tier")


# ── card_templates ─────────────────────────────────────────────────────────────

class CardTemplate(Base, TimestampMixin):
    """Design visuel d'une carte fidélité virtuelle (couleur, logo, image)."""
    __tablename__ = "card_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_tiers.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    background_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#1A1A2E")
    text_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#FFFFFF")
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    background_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    tier: Mapped[Optional["LoyaltyTier"]] = relationship(back_populates="templates")


# ── loyalty_cards ──────────────────────────────────────────────────────────────

class LoyaltyCard(Base, TimestampMixin):
    """
    Carte fidélité d'un client.
    card_type='native'   → émise par un programme du commerçant (program_id requis)
    card_type='external' → importée manuellement (external_issuer + external_ref)

    points_balance : valeur commerciale définie par le marchand. JAMAIS un solde financier Fiissa.
    """
    __tablename__ = "loyalty_cards"
    __table_args__ = (
        UniqueConstraint("company_id", "card_number", name="uq_loyalty_card_number_per_company"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_programs.id", ondelete="SET NULL"), nullable=True
    )
    tier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_tiers.id", ondelete="SET NULL"), nullable=True
    )
    card_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_templates.id", ondelete="SET NULL"), nullable=True
    )
    card_number: Mapped[str] = mapped_column(String(32), nullable=False)
    points_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    card_type: Mapped[str] = mapped_column(
        SAEnum(*CARD_TYPE_VALUES, name="loyalty_card_type_enum"), nullable=False, default="native"
    )
    external_issuer: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    external_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(*CARD_STATUS_VALUES, name="loyalty_card_status_enum"), nullable=False, default="active"
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    program: Mapped[Optional["LoyaltyProgram"]] = relationship(back_populates="cards")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    transactions: Mapped[list["LoyaltyTransaction"]] = relationship(back_populates="card")


# ── loyalty_transactions ───────────────────────────────────────────────────────

class LoyaltyTransaction(Base):
    """
    Ledger append-only des mouvements de points.
    AUCUN update ou delete n'est autorisé sur cette table.
    points_delta > 0 : gain | points_delta < 0 : dépense/expiration
    """
    __tablename__ = "loyalty_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(
        SAEnum(*TRANSACTION_TYPE_VALUES, name="loyalty_tx_type_enum"), nullable=False
    )
    points_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    points_before: Mapped[int] = mapped_column(Integer, nullable=False)
    points_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    card: Mapped["LoyaltyCard"] = relationship(back_populates="transactions")


# ── loyalty_rewards ────────────────────────────────────────────────────────────

class LoyaltyReward(Base, TimestampMixin):
    __tablename__ = "loyalty_rewards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_type: Mapped[str] = mapped_column(
        SAEnum(*REWARD_TYPE_VALUES, name="loyalty_reward_type_enum"), nullable=False
    )
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    max_redemptions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    redemptions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    program: Mapped["LoyaltyProgram"] = relationship(back_populates="rewards")
    coupons: Mapped[list["LoyaltyCoupon"]] = relationship(back_populates="reward")


# ── loyalty_coupons ────────────────────────────────────────────────────────────

class LoyaltyCoupon(Base, TimestampMixin):
    __tablename__ = "loyalty_coupons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reward_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_rewards.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    discount_type: Mapped[str] = mapped_column(
        SAEnum(*DISCOUNT_TYPE_VALUES, name="coupon_discount_type_enum"), nullable=False
    )
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    min_order_xof: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reward: Mapped[Optional["LoyaltyReward"]] = relationship(back_populates="coupons")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])


# ── customer_scores ────────────────────────────────────────────────────────────

class CustomerScore(Base, TimestampMixin):
    """
    Score RFM (Recency, Frequency, Monetary) calculé par tâche Celery quotidienne.
    Un seul score par (company_id, customer_id).
    """
    __tablename__ = "customer_scores"
    __table_args__ = (
        UniqueConstraint("company_id", "customer_id", name="uq_customer_score_per_company"),
        Index("ix_customer_scores_company_segment", "company_id", "segment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recency_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frequency_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monetary_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rfm_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    segment: Mapped[str] = mapped_column(
        SAEnum(*SEGMENT_VALUES, name="customer_segment_enum"), nullable=False, default="new"
    )
    last_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_spent_xof: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
