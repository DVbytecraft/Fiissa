"""
Modèles : Category, Product, StockMovement
Règle : prix sauvegardé en entier (francs CFA), jamais en float.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, func,
    Enum as SAEnum, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin

CATEGORY_SOURCE_MODES = ("internal", "csv_import", "external_api", "hybrid")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("company_id", "slug", name="uq_category_company_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    company: Mapped["Company"] = relationship(foreign_keys=[company_id])
    store: Mapped[Optional["Store"]] = relationship(foreign_keys=[store_id], back_populates="categories")
    parent: Mapped[Optional["Category"]] = relationship(
        remote_side="Category.id",
        foreign_keys=[parent_id],
        back_populates="children",
        overlaps="children",
    )
    children: Mapped[list["Category"]] = relationship(
        foreign_keys=[parent_id],
        back_populates="parent",
        overlaps="parent",
    )
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_company_barcode", "company_id", "barcode"),
        Index("ix_products_company_category", "company_id", "category_id"),
        Index("ix_products_company_available", "company_id", "is_available"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    origin_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), default="pièce")
    # Poids et dimensions physiques (informations produit, pas pricing)
    weight_g: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    volume_ml: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dimensions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Prix en francs CFA entiers — JAMAIS de float
    price_xof: Mapped[int] = mapped_column(Integer, nullable=False)
    compare_price_xof: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tax_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Images : image principale + galerie supplémentaire
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Attributs libres (couleur, taille, saveur, etc.) + tags (bio, halal, promo…)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Quantités min/max par commande
    min_order_qty: Mapped[int] = mapped_column(Integer, default=1)
    max_order_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    # Stock
    track_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0)
    stock_alert_qty: Mapped[int] = mapped_column(Integer, default=5)
    source_type: Mapped[str] = mapped_column(
        SAEnum("internal", "csv_import", "external_sync", name="product_source_type_enum"),
        default="internal",
    )

    # Relations
    company: Mapped["Company"] = relationship(foreign_keys=[company_id])
    store: Mapped[Optional["Store"]] = relationship(foreign_keys=[store_id], back_populates="products")
    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="product")

    @property
    def stock_available(self) -> int:
        """Stock réellement disponible (hors réservations)."""
        return max(0, self.stock_quantity - self.stock_reserved)

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price_xof}>"


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    type: Mapped[str] = mapped_column(
        SAEnum(
            "purchase", "sale", "return", "adjustment",
            "reservation", "reservation_release", "loss",
            name="stock_movement_type_enum",
        ),
        nullable=False,
    )
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product: Mapped["Product"] = relationship(back_populates="stock_movements")
    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_id])


class ProductHistory(Base):
    __tablename__ = "product_history"
    __table_args__ = (
        Index("ix_product_history_product_created", "product_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    changed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_type: Mapped[str] = mapped_column(
        SAEnum("price", "stock", "availability", "metadata", name="product_history_type_enum"),
        nullable=False,
    )
    old_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product: Mapped["Product"] = relationship(foreign_keys=[product_id])
    changed_by: Mapped[Optional["User"]] = relationship(foreign_keys=[changed_by_id])


class CatalogSource(Base, TimestampMixin):
    __tablename__ = "catalog_sources"
    __table_args__ = (
        UniqueConstraint("company_id", "store_id", name="uq_catalog_source_company_store"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    mode: Mapped[str] = mapped_column(
        SAEnum(*CATEGORY_SOURCE_MODES, name="catalog_source_mode_enum"),
        default="internal",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class CatalogImportJob(Base, TimestampMixin):
    __tablename__ = "catalog_import_jobs"
    __table_args__ = (
        Index("ix_catalog_import_jobs_company_created", "company_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "processing", "completed", "failed", name="catalog_import_status_enum"),
        default="pending",
    )
    source_format: Mapped[str] = mapped_column(
        SAEnum("csv", "xlsx", name="catalog_import_format_enum"), default="csv"
    )
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    errors: Mapped[list["CatalogImportError"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class CatalogImportError(Base):
    __tablename__ = "catalog_import_errors"
    __table_args__ = (
        Index("ix_catalog_import_errors_job_row", "job_id", "row_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalog_import_jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_row: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job: Mapped["CatalogImportJob"] = relationship(back_populates="errors")


class ProductSyncJob(Base):
    __tablename__ = "product_sync_jobs"
    __table_args__ = (
        Index("ix_product_sync_jobs_company_created", "company_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_integrations.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "running", "completed", "failed", name="product_sync_status_enum"),
        default="pending",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sync_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


from apps.companies.models import Company  # noqa: E402
from apps.stores.models import Store  # noqa: E402
from apps.users.models import User  # noqa: E402
