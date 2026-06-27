"""
Modèle : Payment
Règles critiques :
- transaction_ref unique par (company_id, operator) → pas de double paiement
- Un paiement confirmé ne peut PAS être re-confirmé
- Toute action de confirmation est loguée
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, ForeignKey, Integer, String, Text, Enum as SAEnum, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin
from core.state_machine import PAYMENT_STATUS_VALUES

PAYMENT_OPERATORS = (
    "orange_money", "wave", "mtn_momo", "moov_money",
    "free_money", "tmoney", "flooz", "fedapay", 
    "cash", "manual", "other",
)

PAYMENT_METHODS = ("mobile_money", "card", "cash", "gateway", "manual")

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        # Empêche le double paiement avec la même référence chez le même opérateur pour la même entreprise
        UniqueConstraint(
            "company_id", "operator", "transaction_ref",
            name="uq_payment_company_operator_ref",
        ),
        Index("ix_payments_company_status", "company_id", "status"),
        Index("ix_payments_company_order", "company_id", "order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    payment_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)

    method: Mapped[str] = mapped_column(
        SAEnum(*PAYMENT_METHODS, name="payment_method_enum"), nullable=False
    )
    operator: Mapped[str] = mapped_column(
        SAEnum(*PAYMENT_OPERATORS, name="payment_operator_enum"), nullable=False
    )
    amount_xof: Mapped[int] = mapped_column(Integer, nullable=False)

    # Informations fournies par le client
    sender_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    transaction_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    status: Mapped[str] = mapped_column(
        SAEnum(*PAYMENT_STATUS_VALUES, name="payment_status_enum"),
        default="pending",
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Confirmation
    confirmed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rejet
    rejected_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Remboursement
    refunded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refund_amount_xof: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Réponse API passerelle (V2)
    gateway_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relations
    order: Mapped["Order"] = relationship(back_populates="payment")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    confirmed_by: Mapped[Optional["User"]] = relationship(foreign_keys=[confirmed_by_id])
    rejected_by: Mapped[Optional["User"]] = relationship(foreign_keys=[rejected_by_id])
    store: Mapped["Store"] = relationship(foreign_keys=[store_id])
    receipt: Mapped[Optional["Receipt"]] = relationship(back_populates="payment", uselist=False)

    @property
    def is_confirmed(self) -> bool:
        return self.status == "confirmed"

    @property
    def can_be_confirmed(self) -> bool:
        return self.status == "pending_verification"

    def __repr__(self) -> str:
        return f"<Payment {self.payment_number} status={self.status} amount={self.amount_xof}>"


from apps.orders.models import Order  # noqa: E402
from apps.users.models import User  # noqa: E402
from apps.stores.models import Store  # noqa: E402
from apps.receipts.models import Receipt  # noqa: E402
