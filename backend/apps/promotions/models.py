"""
Modèle : Promotion
Types supportés :
  - percentage  : réduction en % sur le total commande
  - fixed       : montant fixe déduit (ex : -500 XOF)
  - bogo        : achetez N obtenez N gratuits (appliqué sur les items)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Index, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TimestampMixin

PROMOTION_TYPES = ("percentage", "fixed", "bogo")
PROMOTION_APPLIES_TO = ("all", "category", "product")


class Promotion(Base, TimestampMixin):
    """
    Promotion / code promo défini par un marchand.

    - `applies_to` = "all"      → s'applique à toute commande
    - `applies_to` = "category" → `target_ids` contient des category_id (UUIDs)
    - `applies_to` = "product"  → `target_ids` contient des product_id (UUIDs)
    """
    __tablename__ = "promotions"
    __table_args__ = (
        Index("ix_promotions_company_active", "company_id", "is_active"),
        Index("ix_promotions_code", "company_id", "code", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    type: Mapped[str] = mapped_column(
        SAEnum(*PROMOTION_TYPES, name="promotion_type_enum"), nullable=False
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    applies_to: Mapped[str] = mapped_column(
        SAEnum(*PROMOTION_APPLIES_TO, name="promotion_applies_to_enum"),
        nullable=False, default="all",
    )
    target_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    min_order_xof: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, default=0)

    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stackable: Mapped[bool] = mapped_column(Boolean, default=False)
