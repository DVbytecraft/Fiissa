"""
Modèle : Store (magasin physique d'une entreprise)
"""

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin


class Store(Base, TimestampMixin):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Géolocalisation
    geo_lat: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    geo_lng: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    # Horaires JSONB : {"mon": {"open": "08:00", "close": "20:00"}, ...}
    opening_hours: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # État
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Services disponibles
    scan_go_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    click_collect_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Frais de livraison
    delivery_fee_xof: Mapped[int] = mapped_column(default=0)
    free_delivery_threshold_xof: Mapped[Optional[int]] = mapped_column(nullable=True)
    # Mobile Money : {"operator": "wave", "number": "77123456", "account_name": "Fatou Shop"}
    mobile_money_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Image de couverture
    cover_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relations
    company: Mapped["Company"] = relationship(back_populates="stores")
    categories: Mapped[list["Category"]] = relationship(back_populates="store")
    products: Mapped[list["Product"]] = relationship(back_populates="store")
    orders: Mapped[list["Order"]] = relationship(back_populates="store")

    def __repr__(self) -> str:
        return f"<Store id={self.id} name={self.name} company={self.company_id}>"


from apps.companies.models import Company  # noqa: E402
from apps.catalog.models import Category, Product  # noqa: E402
from apps.orders.models import Order  # noqa: E402
