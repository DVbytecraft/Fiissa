"""Add merchant_api_keys table

Revision ID: 0014_merchant_api_keys
Revises: 0013_loyalty_validation_mode
Create Date: 2026-06-27
"""

from alembic import op


revision = "0014_merchant_api_keys"
down_revision = "0013_loyalty_validation_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS merchant_api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
            key_hash VARCHAR(64) NOT NULL UNIQUE,
            masked_preview VARCHAR(60) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_merchant_api_keys_key_hash ON merchant_api_keys(key_hash)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_merchant_api_keys_company_id ON merchant_api_keys(company_id)")


def downgrade() -> None:
    op.drop_index("ix_merchant_api_keys_key_hash", table_name="merchant_api_keys")
    op.drop_index("ix_merchant_api_keys_company_id", table_name="merchant_api_keys")
    op.drop_table("merchant_api_keys")
