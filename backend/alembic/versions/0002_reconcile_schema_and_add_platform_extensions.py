"""Reconcile ORM drift and add platform extension tables

Revision ID: 0002_platform_extensions
Revises: 0001_initial
Create Date: 2026-06-23 23:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "0002_platform_extensions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(name: str, table_name: str, columns: list[str], unique: bool = False) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if name not in existing:
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # Existing table reconciliation
    _add_column_if_missing("users", sa.Column("avatar_url", sa.Text(), nullable=True))
    _add_column_if_missing("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    _add_column_if_missing(
        "user_company_roles", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"))
    )

    _add_column_if_missing("otp_codes", sa.Column("phone", sa.String(30), nullable=True))
    op.execute(
        """
        UPDATE otp_codes otp
        SET phone = users.phone
        FROM users
        WHERE otp.user_id = users.id AND otp.phone IS NULL
        """
    )

    for column in (
        sa.Column("country", sa.String(5), nullable=True, server_default="SN"),
        sa.Column("currency", sa.String(5), nullable=True, server_default="XOF"),
        sa.Column("timezone", sa.String(60), nullable=True, server_default="Africa/Dakar"),
        sa.Column("address", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rccm", sa.String(100), nullable=True),
        sa.Column("tax_id", sa.String(100), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
    ):
        _add_column_if_missing("companies", column)

    for column in (
        sa.Column("slug", sa.String(120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("delivery_fee_xof", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
    ):
        _add_column_if_missing("stores", column)

    for column in (
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    ):
        _add_column_if_missing("categories", column)

    for column in (
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(50), nullable=False, server_default="piece"),
        sa.Column("compare_price_xof", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="internal"),
    ):
        _add_column_if_missing("products", column)

    for column in (
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity_before", sa.Integer(), nullable=True),
        sa.Column("quantity_after", sa.Integer(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    ):
        _add_column_if_missing("stock_movements", column)

    if _has_column(inspector, "stock_movements", "stock_before"):
        op.execute("UPDATE stock_movements SET quantity_before = stock_before WHERE quantity_before IS NULL")
    if _has_column(inspector, "stock_movements", "stock_after"):
        op.execute("UPDATE stock_movements SET quantity_after = stock_after WHERE quantity_after IS NULL")

    _add_column_if_missing("carts", sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add_column_if_missing("carts", sa.Column("type", sa.String(30), nullable=True))
    _add_column_if_missing("carts", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    if _has_column(inspector, "carts", "user_id"):
        op.execute("UPDATE carts SET customer_id = user_id WHERE customer_id IS NULL")
    if _has_column(inspector, "carts", "order_type"):
        op.execute("UPDATE carts SET type = order_type WHERE type IS NULL")

    _add_column_if_missing("cart_items", sa.Column("unit_price_xof", sa.Integer(), nullable=True))

    for column in (
        sa.Column("type", sa.String(30), nullable=True),
        sa.Column("subtotal_xof", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount_xof", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivery_fee_xof", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("pickup_code", sa.String(10), nullable=True),
        sa.Column("prepared_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_reason", sa.Text(), nullable=True),
    ):
        _add_column_if_missing("orders", column)
    if _has_column(inspector, "orders", "order_type"):
        op.execute("UPDATE orders SET type = order_type WHERE type IS NULL")
    if _has_column(inspector, "orders", "cancellation_reason"):
        op.execute("UPDATE orders SET cancelled_reason = cancellation_reason WHERE cancelled_reason IS NULL")
    op.execute("UPDATE orders SET subtotal_xof = total_xof WHERE subtotal_xof = 0 AND total_xof IS NOT NULL")
    op.execute(
        """
        ALTER TABLE orders
        ALTER COLUMN delivery_address TYPE jsonb
        USING CASE
            WHEN delivery_address IS NULL OR trim(delivery_address) = '' THEN NULL
            ELSE delivery_address::jsonb
        END
        """
    )

    _add_column_if_missing("order_items", sa.Column("subtotal_xof", sa.Integer(), nullable=True))
    _add_column_if_missing("order_items", sa.Column("notes", sa.Text(), nullable=True))
    if _has_column(inspector, "order_items", "total_xof"):
        op.execute("UPDATE order_items SET subtotal_xof = total_xof WHERE subtotal_xof IS NULL")

    for column in (
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    ):
        _add_column_if_missing("pickups", column)

    for column in (
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(30), nullable=True),
        sa.Column("used_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    ):
        _add_column_if_missing("order_qr_codes", column)

    for column in (
        sa.Column("deliverer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delivery_notes", sa.Text(), nullable=True),
    ):
        _add_column_if_missing("deliveries", column)
    op.execute(
        """
        ALTER TABLE deliveries
        ALTER COLUMN address TYPE jsonb
        USING CASE
            WHEN address IS NULL OR trim(address) = '' THEN NULL
            ELSE address::jsonb
        END
        """
    )

    for column in (
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gateway_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    ):
        _add_column_if_missing("payments", column)
    op.execute(
        """
        UPDATE payments p
        SET store_id = o.store_id
        FROM orders o
        WHERE p.order_id = o.id AND p.store_id IS NULL
        """
    )

    for column in (
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pdf_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_xof", sa.Integer(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="generated"),
    ):
        _add_column_if_missing("receipts", column)
    if _has_column(inspector, "receipts", "total_xof"):
        op.execute("UPDATE receipts SET amount_xof = total_xof WHERE amount_xof IS NULL")
    if _has_column(inspector, "receipts", "created_at"):
        op.execute("UPDATE receipts SET issued_at = created_at WHERE issued_at IS NULL")
    op.execute(
        """
        UPDATE receipts r
        SET store_id = o.store_id,
            customer_id = o.customer_id
        FROM orders o
        WHERE r.order_id = o.id
          AND (r.store_id IS NULL OR r.customer_id IS NULL)
        """
    )

    # New platform tables
    if not _has_table(inspector, "plans"):
        op.create_table(
            "plans",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("billing_cycle", sa.String(30), nullable=False, server_default="monthly"),
            sa.Column("amount_xof", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("commission_rate", sa.Numeric(5, 4), nullable=False, server_default="0.0000"),
            sa.Column("features", postgresql.JSONB(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )

    if not _has_table(inspector, "company_settings"):
        op.create_table(
            "company_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("currency", sa.String(5), nullable=False, server_default="XOF"),
            sa.Column("timezone", sa.String(60), nullable=False, server_default="Africa/Dakar"),
            sa.Column("language", sa.String(10), nullable=False, server_default="fr"),
            sa.Column("catalog_mode", sa.String(30), nullable=False, server_default="internal"),
            sa.Column("payment_mode", sa.String(30), nullable=False, server_default="manual"),
            sa.Column("delivery_mode", sa.String(30), nullable=False, server_default="pickup"),
            sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
            sa.Column("extra", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id"),
        )

    if not _has_table(inspector, "feature_flags"):
        op.create_table(
            "feature_flags",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("key", sa.String(100), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("config", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "key", name="uq_feature_flag_company_key"),
        )

    if not _has_table(inspector, "subscription_invoices"):
        op.create_table(
            "subscription_invoices",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("invoice_number", sa.String(80), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="issued"),
            sa.Column("amount_xof", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tax_xof", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_xof", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("invoice_number"),
        )

    if not _has_table(inspector, "subscription_renewals"):
        op.create_table(
            "subscription_renewals",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("previous_period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("new_period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "product_history"):
        op.create_table(
            "product_history",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("changed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("change_type", sa.String(30), nullable=False),
            sa.Column("old_data", postgresql.JSONB(), nullable=True),
            sa.Column("new_data", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "notification_templates"):
        op.create_table(
            "notification_templates",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("event_key", sa.String(100), nullable=False),
            sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
            sa.Column("subject_template", sa.String(255), nullable=True),
            sa.Column("body_template", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "notification_events"):
        op.create_table(
            "notification_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("event_key", sa.String(100), nullable=False),
            sa.Column("resource_type", sa.String(100), nullable=True),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("payload", postgresql.JSONB(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "support_tickets"):
        op.create_table(
            "support_tickets",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("subject", sa.String(300), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "support_messages"):
        op.create_table(
            "support_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("attachments", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "support_attachments"):
        op.create_table(
            "support_attachments",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("storage_key", sa.Text(), nullable=False),
            sa.Column("content_type", sa.String(120), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["message_id"], ["support_messages.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "api_integrations"):
        op.create_table(
            "api_integrations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(150), nullable=False, server_default="catalog_api"),
            sa.Column("integration_type", sa.String(30), nullable=False, server_default="catalog"),
            sa.Column("endpoint_url", sa.Text(), nullable=False),
            sa.Column("http_method", sa.String(10), nullable=False, server_default="GET"),
            sa.Column("request_headers", postgresql.JSONB(), nullable=True),
            sa.Column("response_mapping", postgresql.JSONB(), nullable=True),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("fallback_to_internal", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("cache_ttl_seconds", sa.Integer(), nullable=False, server_default="300"),
            sa.Column("settings", postgresql.JSONB(), nullable=True),
            sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        for column in (
            sa.Column("http_method", sa.String(10), nullable=False, server_default="GET"),
            sa.Column("request_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("response_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="10"),
        ):
            _add_column_if_missing("api_integrations", column)

    if not _has_table(inspector, "api_credentials"):
        op.create_table(
            "api_credentials",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("credential_type", sa.String(30), nullable=False, server_default="api_key"),
            sa.Column("key_name", sa.String(100), nullable=True),
            sa.Column("encrypted_secret", sa.Text(), nullable=False),
            sa.Column("masked_preview", sa.String(50), nullable=True),
            sa.Column("last_rotated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["integration_id"], ["api_integrations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "api_call_logs"):
        op.create_table(
            "api_call_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("barcode", sa.String(120), nullable=True),
            sa.Column("request_payload", postgresql.JSONB(), nullable=True),
            sa.Column("response_payload", postgresql.JSONB(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("http_status", sa.Integer(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["integration_id"], ["api_integrations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "external_product_cache"):
        op.create_table(
            "external_product_cache",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("barcode", sa.String(120), nullable=False),
            sa.Column("product_payload", postgresql.JSONB(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["integration_id"], ["api_integrations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "catalog_sources"):
        op.create_table(
            "catalog_sources",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("mode", sa.String(30), nullable=False, server_default="internal"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("config", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "store_id", name="uq_catalog_source_company_store"),
        )

    if not _has_table(inspector, "catalog_import_jobs"):
        op.create_table(
            "catalog_import_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("source_format", sa.String(20), nullable=False, server_default="csv"),
            sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_report", sa.Text(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "catalog_import_errors"):
        op.create_table(
            "catalog_import_errors",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("field_name", sa.String(100), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("raw_row", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["job_id"], ["catalog_import_jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "product_sync_jobs"):
        op.create_table(
            "product_sync_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["integration_id"], ["api_integrations.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "webhook_endpoints"):
        op.create_table(
            "webhook_endpoints",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("target_url", sa.Text(), nullable=False),
            sa.Column("secret_encrypted", sa.Text(), nullable=True),
            sa.Column("events", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("payload", postgresql.JSONB(), nullable=False),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["endpoint_id"], ["webhook_endpoints.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing("ix_product_history_product_created", "product_history", ["product_id", "created_at"])
    _create_index_if_missing("ix_notification_events_company_event", "notification_events", ["company_id", "event_key", "created_at"])
    _create_index_if_missing("ix_api_integrations_company_active", "api_integrations", ["company_id", "is_active"])
    _create_index_if_missing("ix_api_call_logs_integration_created", "api_call_logs", ["integration_id", "created_at"])
    _create_index_if_missing("ix_external_product_cache_lookup", "external_product_cache", ["company_id", "barcode"])
    _create_index_if_missing("ix_catalog_import_jobs_company_created", "catalog_import_jobs", ["company_id", "created_at"])
    _create_index_if_missing("ix_catalog_import_errors_job_row", "catalog_import_errors", ["job_id", "row_number"])
    _create_index_if_missing("ix_product_sync_jobs_company_created", "product_sync_jobs", ["company_id", "created_at"])
    _create_index_if_missing("ix_webhook_endpoints_company_active", "webhook_endpoints", ["company_id", "is_active"])
    _create_index_if_missing("ix_webhook_deliveries_endpoint_created", "webhook_deliveries", ["endpoint_id", "created_at"])


def downgrade() -> None:
    # Partial downgrade for newly added platform tables only.
    for table_name in (
        "webhook_deliveries",
        "webhook_endpoints",
        "external_product_cache",
        "product_sync_jobs",
        "catalog_import_errors",
        "catalog_import_jobs",
        "catalog_sources",
        "api_call_logs",
        "api_credentials",
        "api_integrations",
        "support_attachments",
        "support_messages",
        "support_tickets",
        "notification_events",
        "notification_templates",
        "product_history",
        "subscription_renewals",
        "subscription_invoices",
        "feature_flags",
        "company_settings",
        "plans",
    ):
        op.drop_table(table_name)
