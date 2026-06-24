"""Add email support to otp_codes for customer email OTP auth.

Revision ID: 0006_auth_email_otp
Revises: 0005_loyalty_wallet
Create Date: 2026-06-24 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0006_auth_email_otp"
down_revision = "0005_loyalty_wallet"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_column(inspector, "otp_codes", "email"):
        op.add_column("otp_codes", sa.Column("email", sa.String(length=255), nullable=True))
    if not _has_column(inspector, "otp_codes", "phone"):
        op.add_column("otp_codes", sa.Column("phone", sa.String(length=30), nullable=True))

    try:
        op.alter_column("otp_codes", "phone", existing_type=sa.String(length=30), nullable=True)
    except Exception:
        pass

    op.create_index("ix_otp_codes_email", "otp_codes", ["email"], unique=False, if_not_exists=True)


def downgrade() -> None:
    try:
        op.drop_index("ix_otp_codes_email", table_name="otp_codes")
    except Exception:
        pass
    try:
        op.drop_column("otp_codes", "email")
    except Exception:
        pass
