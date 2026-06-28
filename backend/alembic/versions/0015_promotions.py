"""0015 — Système de promotions / codes promo

Revision ID: 0015_promotions
Revises: 0014_merchant_api_keys
Create Date: 2026-06-27
"""

from alembic import op

revision = "0015_promotions"
down_revision = "0014_merchant_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE promotion_type_enum AS ENUM ('percentage', 'fixed', 'bogo');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE promotion_applies_to_enum AS ENUM ('all', 'category', 'product');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            code VARCHAR(50),
            type promotion_type_enum NOT NULL,
            value INTEGER NOT NULL,
            applies_to promotion_applies_to_enum NOT NULL DEFAULT 'all',
            target_ids JSONB,
            min_order_xof INTEGER,
            max_uses INTEGER,
            uses_count INTEGER NOT NULL DEFAULT 0,
            start_at TIMESTAMP WITH TIME ZONE,
            end_at TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            stackable BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_promotions_company_active ON promotions(company_id, is_active)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_promotions_code ON promotions(company_id, code)")
    op.execute("""
        ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS promotion_id UUID REFERENCES promotions(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS promotion_code VARCHAR(50)
    """)


def downgrade() -> None:
    op.drop_column("orders", "promotion_code")
    op.drop_column("orders", "promotion_id")
    op.drop_index("ix_promotions_code", table_name="promotions")
    op.drop_index("ix_promotions_company_active", table_name="promotions")
    op.drop_table("promotions")
    op.execute("DROP TYPE IF EXISTS promotion_type_enum")
    op.execute("DROP TYPE IF EXISTS promotion_applies_to_enum")
