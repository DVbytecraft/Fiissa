"""
Modèle Wallet — wallet_payment_methods

RÈGLE ABSOLUE : Fiissa ne stocke jamais d'argent.
Ce modèle stocke uniquement des références/tokens vers des méthodes de paiement externes.
Aucun solde, aucun fonds ne transite ou n'est conservé ici.

V1 activé : mobile_money, external_loyalty_card
V1 désactivé (feature flags) : bank_card, bank_account
"""

import uuid
from typing import Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    text,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin


METHOD_TYPE_VALUES = ("mobile_money", "external_loyalty_card", "bank_card", "bank_account")
MOBILE_OPERATOR_VALUES = ("wave", "orange_money", "free_money", "mtn_momo")


class WalletPaymentMethod(Base, TimestampMixin):
    """
    Référence vers une méthode de paiement externe d'un client.
    Stocke un identifiant/token — jamais de fonds ni de solde.
    """
    __tablename__ = "wallet_payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    method_type: Mapped[str] = mapped_column(
        SAEnum(*METHOD_TYPE_VALUES, name="wallet_method_type_enum"), nullable=False
    )
    operator: Mapped[Optional[str]] = mapped_column(
        SAEnum(*MOBILE_OPERATOR_VALUES, name="wallet_operator_enum"), nullable=True
    )
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
