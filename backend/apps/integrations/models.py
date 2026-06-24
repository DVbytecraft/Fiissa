"""
Modèles d'integration externe:
- catalogue API entreprise
- webhooks sortants
- cache et logs d'appels
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin


INTEGRATION_STATUS = ("active", "disabled", "error")
CREDENTIAL_TYPE = ("api_key", "bearer", "basic", "custom")
WEBHOOK_EVENT_TYPES = (
    "order.created",
    "order.ready",
    "order.cancelled",
    "payment.confirmed",
    "receipt.generated",
)
DELIVERY_STATUS = ("pending", "success", "failed")


class ApiIntegration(Base, TimestampMixin):
    __tablename__ = "api_integrations"
    __table_args__ = (
        Index("ix_api_integrations_company_active", "company_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, default="catalog_api")
    integration_type: Mapped[str] = mapped_column(
        SAEnum("catalog", "erp", "pos", "stock", name="integration_type_enum"),
        default="catalog",
    )
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    http_method: Mapped[str] = mapped_column(
        SAEnum("GET", "POST", name="integration_http_method_enum"),
        default="GET",
    )
    request_headers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    response_mapping: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)
    fallback_to_internal: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, default=300)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(
        SAEnum(*INTEGRATION_STATUS, name="integration_status_enum"), default="active"
    )

    credentials: Mapped[list["ApiCredential"]] = relationship(
        back_populates="integration", cascade="all, delete-orphan"
    )
    call_logs: Mapped[list["ApiCallLog"]] = relationship(
        back_populates="integration", cascade="all, delete-orphan"
    )
    product_cache_entries: Mapped[list["ExternalProductCache"]] = relationship(
        back_populates="integration", cascade="all, delete-orphan"
    )


class ApiCredential(Base, TimestampMixin):
    __tablename__ = "api_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credential_type: Mapped[str] = mapped_column(
        SAEnum(*CREDENTIAL_TYPE, name="credential_type_enum"), default="api_key"
    )
    key_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    masked_preview: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    integration: Mapped["ApiIntegration"] = relationship(back_populates="credentials")


class ApiCallLog(Base):
    __tablename__ = "api_call_logs"
    __table_args__ = (
        Index("ix_api_call_logs_integration_created", "integration_id", "created_at"),
        Index("ix_api_call_logs_company_status", "company_id", "http_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    barcode: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    request_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    integration: Mapped["ApiIntegration"] = relationship(back_populates="call_logs")


class ExternalProductCache(Base):
    __tablename__ = "external_product_cache"
    __table_args__ = (
        Index("ix_external_product_cache_lookup", "company_id", "barcode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    barcode: Mapped[str] = mapped_column(String(120), nullable=False)
    product_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    integration: Mapped["ApiIntegration"] = relationship(back_populates="product_cache_entries")


class WebhookEndpoint(Base, TimestampMixin):
    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        Index("ix_webhook_endpoints_company_active", "company_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    events: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="endpoint", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_endpoint_created", "endpoint_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        SAEnum(*WEBHOOK_EVENT_TYPES, name="webhook_event_type_enum"), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(*DELIVERY_STATUS, name="webhook_delivery_status_enum"), default="pending"
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    endpoint: Mapped["WebhookEndpoint"] = relationship(back_populates="deliveries")
