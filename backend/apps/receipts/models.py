"""
Modèle : Receipt
Règle : un reçu généré est IMMUABLE. Le html_content est un snapshot.
Le PDF est stocké en S3/MinIO et ne peut jamais être regénéré à l'identique.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.state_machine import RECEIPT_STATUS_VALUES


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False, unique=True, index=True,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False, unique=True, index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    receipt_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    # Code unique pour QR code de vérification — endpoint public
    verification_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Snapshot HTML immuable du reçu
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    # PDF stocké en objet storage
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(*RECEIPT_STATUS_VALUES, name="receipt_status_enum"),
        default="generated",
        index=True,
    )

    amount_xof: Mapped[int] = mapped_column(Integer, nullable=False)
    # Vérification par agent sécurité (scan sortie)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relations
    order: Mapped["Order"] = relationship(back_populates="receipt")
    payment: Mapped["Payment"] = relationship(back_populates="receipt")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    verified_by: Mapped[Optional["User"]] = relationship(foreign_keys=[verified_by_id])
    store: Mapped["Store"] = relationship(foreign_keys=[store_id])

    def __repr__(self) -> str:
        return f"<Receipt {self.receipt_number} amount={self.amount_xof}>"


from apps.orders.models import Order  # noqa: E402
from apps.payments.models import Payment  # noqa: E402
from apps.users.models import User  # noqa: E402
from apps.stores.models import Store  # noqa: E402
