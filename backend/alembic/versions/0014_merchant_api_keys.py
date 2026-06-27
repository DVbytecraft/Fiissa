"""Add merchant_api_keys table

Revision ID: 0014_merchant_api_keys
Revises: 0013_loyalty_validation_mode
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "0014_merchant_api_keys"
down_revision = "0013_loyalty_validation_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("masked_preview", sa.String(60), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_merchant_api_keys_key_hash", "merchant_api_keys", ["key_hash"], unique=True)
    op.create_index("ix_merchant_api_keys_company_id", "merchant_api_keys", ["company_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_merchant_api_keys_key_hash", table_name="merchant_api_keys")
    op.drop_index("ix_merchant_api_keys_company_id", table_name="merchant_api_keys")
    op.drop_table("merchant_api_keys")
