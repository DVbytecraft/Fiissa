"""Align PostgreSQL enum types with ORM models for production runtime.

Revision ID: 0008_postgres_enum_alignment
Revises: 0007_merchant_onboarding_idempotency
Create Date: 2026-06-24 13:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0008_postgres_enum_alignment"
down_revision = "0007_merchant_onboarding_idempotency"
branch_labels = None
depends_on = None


ENUM_COLUMNS: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("companies", "type", "company_type_enum", ("boutique", "supermarket", "restaurant", "proximity", "pharmacy", "other")),
    ("subscriptions", "plan", "subscription_plan_enum", ("starter", "pro", "enterprise")),
    ("subscriptions", "status", "subscription_status_enum", ("trial", "active", "suspended", "cancelled")),
    ("subscriptions", "billing_cycle", "billing_cycle_enum", ("monthly", "yearly")),
    ("plans", "billing_cycle", "plan_billing_cycle_enum", ("monthly", "yearly")),
    ("subscription_invoices", "status", "subscription_invoice_status_enum", ("draft", "issued", "paid", "void")),
    ("subscription_renewals", "status", "subscription_renewal_status_enum", ("scheduled", "processed", "failed")),
    ("company_settings", "catalog_mode", "catalog_mode_enum", ("internal", "csv_import", "external_api", "hybrid")),
    ("company_settings", "payment_mode", "payment_mode_enum", ("manual", "gateway", "hybrid")),
    ("company_settings", "delivery_mode", "delivery_mode_enum", ("pickup", "delivery", "hybrid")),
    ("user_company_roles", "role", "user_role_enum", ("super_admin", "company_owner", "store_manager", "cashier", "accountant", "preparer", "security_agent", "support_agent", "customer")),
    ("products", "source_type", "product_source_type_enum", ("internal", "csv_import", "external_sync")),
    ("stock_movements", "type", "stock_movement_type_enum", ("purchase", "sale", "return", "adjustment", "reservation", "reservation_release", "loss")),
    ("product_history", "change_type", "product_history_type_enum", ("price", "stock", "availability", "metadata")),
    ("catalog_sources", "mode", "catalog_source_mode_enum", ("internal", "csv_import", "external_api", "hybrid")),
    ("catalog_import_jobs", "status", "catalog_import_status_enum", ("pending", "processing", "completed", "failed")),
    ("catalog_import_jobs", "source_format", "catalog_import_format_enum", ("csv", "xlsx")),
    ("product_sync_jobs", "status", "product_sync_status_enum", ("pending", "running", "completed", "failed")),
    ("carts", "type", "order_type_enum", ("click_collect", "delivery", "scan_go")),
    ("orders", "type", "order_type_enum", ("click_collect", "delivery", "scan_go")),
    ("orders", "status", "order_status_enum", ("draft", "pending", "awaiting_payment", "payment_submitted", "confirmed", "preparing", "ready", "out_for_delivery", "delivered", "cancelled", "refunded")),
    ("deliveries", "status", "delivery_status_enum", ("pending", "assigned", "picked_up", "in_transit", "delivered", "failed")),
    ("pickups", "status", "pickup_status_enum", ("pending", "ready", "completed", "expired")),
    ("order_qr_codes", "type", "qr_type_enum", ("pickup", "receipt", "scan_go")),
    ("payments", "method", "payment_method_enum", ("mobile_money", "card", "cash", "gateway")),
    ("payments", "operator", "payment_operator_enum", ("orange_money", "wave", "mtn_momo", "moov_money", "free_money", "fedapay", "cash", "other")),
    ("payments", "status", "payment_status_enum", ("pending", "pending_verification", "proof_submitted", "confirmed", "rejected", "failed", "expired", "refunded")),
    ("receipts", "status", "receipt_status_enum", ("generated", "verified", "invalidated")),
    ("notifications", "type", "notification_type_enum", ("order_confirmed", "order_ready", "order_cancelled", "payment_received", "payment_rejected", "payment_reminder", "receipt_ready", "stock_alert", "subscription_expiring")),
    ("notifications", "channel", "notification_channel_enum", ("push", "sms", "email", "in_app")),
    ("notification_templates", "channel", "notification_template_channel_enum", ("push", "sms", "email", "in_app")),
    ("notification_events", "status", "notification_event_status_enum", ("pending", "processed", "failed")),
    ("support_tickets", "status", "ticket_status_enum", ("open", "in_progress", "resolved", "closed")),
    ("support_tickets", "priority", "ticket_priority_enum", ("low", "medium", "high", "urgent")),
    ("api_integrations", "integration_type", "integration_type_enum", ("catalog", "erp", "pos", "stock")),
    ("api_integrations", "http_method", "integration_http_method_enum", ("GET", "POST")),
    ("api_integrations", "status", "integration_status_enum", ("active", "disabled", "error")),
    ("api_credentials", "credential_type", "credential_type_enum", ("api_key", "bearer", "basic", "custom")),
    ("webhook_deliveries", "event_type", "webhook_event_type_enum", ("order.created", "order.ready", "order.cancelled", "payment.confirmed", "receipt.generated")),
    ("webhook_deliveries", "status", "webhook_delivery_status_enum", ("pending", "success", "failed")),
]


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_type(enum_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": enum_name},
    ).scalar()
    return bool(result)


def _column_udt(table_name: str, column_name: str) -> tuple[str | None, str | None]:
    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            """
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).mappings().first()
    if not row:
        return None, None
    return row["data_type"], row["udt_name"]


def _create_enum(enum_name: str, values: tuple[str, ...]) -> None:
    if _has_type(enum_name):
        return
    quoted_values = ", ".join(f"'{value}'" for value in values)
    op.execute(sa.text(f"CREATE TYPE {enum_name} AS ENUM ({quoted_values})"))


def _alter_column_to_enum(table_name: str, column_name: str, enum_name: str) -> None:
    data_type, udt_name = _column_udt(table_name, column_name)
    if data_type == "USER-DEFINED" and udt_name == enum_name:
        return

    op.execute(sa.text(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP DEFAULT"))
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {table_name}
            ALTER COLUMN {column_name}
            TYPE {enum_name}
            USING {column_name}::text::{enum_name}
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table_name, column_name, enum_name, values in ENUM_COLUMNS:
        if not _has_table(inspector, table_name) or not _has_column(inspector, table_name, column_name):
            continue
        _create_enum(enum_name, values)
        _alter_column_to_enum(table_name, column_name, enum_name)


def downgrade() -> None:
    # Intentionally no-op: downgrading enum-backed production columns to plain strings
    # would be lossy and risky.
    pass
