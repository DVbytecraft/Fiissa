"""
Modèles : Cart, CartItem, Order, OrderItem, Delivery, Pickup, OrderQRCode
Machine à états commande : draft→pending→awaiting_payment→payment_submitted
  →confirmed→preparing→ready→(out_for_delivery→)delivered
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, func,
    Enum as SAEnum, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin
from core.state_machine import ORDER_STATUS_VALUES

ORDER_TYPE_VALUES = ("click_collect", "delivery", "scan_go")


class Cart(Base, TimestampMixin):
    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        SAEnum(*ORDER_TYPE_VALUES, name="order_type_enum"), default="click_collect"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    store: Mapped["Store"] = relationship(foreign_keys=[store_id])


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"
    __table_args__ = (
        # Un seul item par produit par panier
        Index("uq_cart_product", "cart_id", "product_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_xof: Mapped[int] = mapped_column(Integer, nullable=False)

    cart: Mapped["Cart"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(foreign_keys=[product_id])


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_company_status", "company_id", "status"),
        Index("ix_orders_company_customer", "company_id", "customer_id"),
        Index("ix_orders_company_created", "company_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        SAEnum(*ORDER_TYPE_VALUES, name="order_type_enum", create_constraint=False)
    )
    status: Mapped[str] = mapped_column(
        SAEnum(*ORDER_STATUS_VALUES, name="order_status_enum"),
        default="draft",
        index=True,
    )
    # Montants en XOF entiers
    subtotal_xof: Mapped[int] = mapped_column(Integer, default=0)
    discount_xof: Mapped[int] = mapped_column(Integer, default=0)
    delivery_fee_xof: Mapped[int] = mapped_column(Integer, default=0)
    total_xof: Mapped[int] = mapped_column(Integer, default=0)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    pickup_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    # Suivi des actions
    prepared_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    prepared_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Expiration paiement (30 min après creation)
    payment_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relations
    store: Mapped["Store"] = relationship(foreign_keys=[store_id], back_populates="orders")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    prepared_by: Mapped[Optional["User"]] = relationship(foreign_keys=[prepared_by_id])
    cancelled_by: Mapped[Optional["User"]] = relationship(foreign_keys=[cancelled_by_id])
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="order", uselist=False)
    receipt: Mapped[Optional["Receipt"]] = relationship(back_populates="order", uselist=False)
    delivery: Mapped[Optional["Delivery"]] = relationship(back_populates="order", uselist=False)
    pickup: Mapped[Optional["Pickup"]] = relationship(back_populates="order", uselist=False)
    qr_code: Mapped[Optional["OrderQRCode"]] = relationship(back_populates="order", uselist=False)

    def __repr__(self) -> str:
        return f"<Order {self.order_number} status={self.status} total={self.total_xof}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable : produit peut être supprimé mais item reste
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    # Snapshots immuables au moment de la commande
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    product_barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit_price_xof: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_xof: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped[Optional["Product"]] = relationship(foreign_keys=[product_id])


class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    deliverer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    address: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "assigned", "picked_up", "in_transit", "delivered", "failed",
               name="delivery_status_enum"),
        default="pending",
    )
    estimated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="delivery")
    deliverer: Mapped[Optional["User"]] = relationship(foreign_keys=[deliverer_id])


PICKUP_FULFILLMENT_VALUES = ("self_pickup", "delegate", "company_delivery", "own_courier")
DELEGATE_ID_TYPE_VALUES = ("carte_identite", "passeport", "permis", "photo")


class Pickup(Base, TimestampMixin):
    __tablename__ = "pickups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    pickup_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "ready", "completed", "expired", "cancelled", name="pickup_status_enum"),
        default="pending",
    )
    # ── Méthode de récupération ──────────────────────────────────────────────
    fulfillment_method: Mapped[str] = mapped_column(
        SAEnum(*PICKUP_FULFILLMENT_VALUES, name="pickup_fulfillment_enum"),
        nullable=False, default="self_pickup",
    )
    # ── Procuration (delegate) ───────────────────────────────────────────────
    delegate_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delegate_last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delegate_id_type: Mapped[Optional[str]] = mapped_column(
        SAEnum(*DELEGATE_ID_TYPE_VALUES, name="delegate_id_type_enum"), nullable=True
    )
    delegate_id_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delegate_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # ── Coursier personnel (own_courier) ─────────────────────────────────────
    courier_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # ── Livraison entreprise (company_delivery) ───────────────────────────────
    delivery_address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # ── Timestamps ───────────────────────────────────────────────────────────
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    order: Mapped["Order"] = relationship(back_populates="pickup")
    verified_by: Mapped[Optional["User"]] = relationship(foreign_keys=[verified_by_id])

    def build_delegate_message(self, customer_full_name: str, order_number: str) -> str:
        """Génère le message pré-rédigé pour le personnel de l'enseigne."""
        return (
            f"Bonjour, je suis {self.delegate_first_name} {self.delegate_last_name} "
            f"et je viens récupérer la commande #{order_number} pour le compte de "
            f"{customer_full_name}. Je peux vous présenter ma pièce d'identité "
            f"({'carte d\'identité' if self.delegate_id_type == 'carte_identite' else self.delegate_id_type or 'document'}) "
            f"pour vérification."
        )


class OrderQRCode(Base):
    __tablename__ = "order_qr_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        SAEnum("pickup", "receipt", "scan_go", name="qr_type_enum")
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="qr_code")
    used_by: Mapped[Optional["User"]] = relationship(foreign_keys=[used_by_id])


from apps.stores.models import Store  # noqa: E402
from apps.users.models import User  # noqa: E402
from apps.catalog.models import Product  # noqa: E402
from apps.payments.models import Payment  # noqa: E402
from apps.receipts.models import Receipt  # noqa: E402
