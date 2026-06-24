"""Add company_registration_requests table and idempotency_key on orders.

Revision ID: 0007_merchant_onboarding_idempotency
Revises: 0006_auth_email_otp
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0007_merchant_onboarding_idempotency"
down_revision = "0006_auth_email_otp"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── company_registration_requests ─────────────────────────────────────────
    if not _has_table(inspector, "company_registration_requests"):
        op.create_table(
            "company_registration_requests",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("uuid_generate_v4()"),
            ),
            # Demandeur
            sa.Column("first_name", sa.String(100), nullable=False),
            sa.Column("last_name", sa.String(100), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("phone", sa.String(30), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            # Entreprise
            sa.Column("company_name", sa.String(255), nullable=False),
            sa.Column("company_type", sa.String(50), nullable=False),
            # Statut
            sa.Column(
                "status",
                sa.Enum("pending", "approved", "rejected", name="registration_request_status_enum"),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("rejection_reason", sa.Text, nullable=True),
            # Révision
            sa.Column("reviewed_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column(
                "reviewed_by_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["reviewed_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email", name="uq_company_reg_request_email"),
        )
        op.create_index(
            "ix_company_registration_requests_email",
            "company_registration_requests",
            ["email"],
        )
        op.create_index(
            "ix_company_registration_requests_status",
            "company_registration_requests",
            ["status"],
        )

    # ── orders.idempotency_key ────────────────────────────────────────────────
    if _has_table(inspector, "orders") and not _has_column(inspector, "orders", "idempotency_key"):
        op.add_column(
            "orders",
            sa.Column("idempotency_key", sa.String(128), nullable=True),
        )
        op.create_index(
            "ix_orders_idempotency_key",
            "orders",
            ["idempotency_key"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # Supprimer idempotency_key
    if _has_table(inspector, "orders") and _has_column(inspector, "orders", "idempotency_key"):
        try:
            op.drop_index("ix_orders_idempotency_key", table_name="orders")
        except Exception:
            pass
        op.drop_column("orders", "idempotency_key")

    # Supprimer la table company_registration_requests
    if _has_table(inspector, "company_registration_requests"):
        op.drop_table("company_registration_requests")

    # Supprimer le type enum si présent
    try:
        sa.Enum(name="registration_request_status_enum").drop(bind, checkfirst=True)
    except Exception:
        pass
