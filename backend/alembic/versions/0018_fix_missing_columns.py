"""0018 — Fix colonnes/tables manquantes (migrations 0010-0017 non appliquées en prod)

Idempotent : IF NOT EXISTS / ADD VALUE IF NOT EXISTS sur tout.
A appliquer si alembic_version est bloqué avant 0010.

Revision ID: 0018_fix_missing_columns
Revises: 0017_payment_refund
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "0018_fix_missing_columns"
down_revision = "0017_payment_refund"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 0010: Product enrichment columns ─────────────────────────────────────
    op.execute("""
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS brand VARCHAR(200),
            ADD COLUMN IF NOT EXISTS origin_country VARCHAR(100),
            ADD COLUMN IF NOT EXISTS weight_g INTEGER,
            ADD COLUMN IF NOT EXISTS volume_ml INTEGER,
            ADD COLUMN IF NOT EXISTS dimensions JSONB,
            ADD COLUMN IF NOT EXISTS tax_rate INTEGER,
            ADD COLUMN IF NOT EXISTS images JSONB,
            ADD COLUMN IF NOT EXISTS attributes JSONB,
            ADD COLUMN IF NOT EXISTS tags JSONB,
            ADD COLUMN IF NOT EXISTS min_order_qty INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS max_order_qty INTEGER
    """)

    # ── 0011: Account lockout ─────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE
    """)

    # ── 0012: Togo operators + manual payment ─────────────────────────────────
    op.execute("ALTER TYPE payment_operator_enum ADD VALUE IF NOT EXISTS 'tmoney'")
    op.execute("ALTER TYPE payment_operator_enum ADD VALUE IF NOT EXISTS 'flooz'")
    op.execute("ALTER TYPE payment_operator_enum ADD VALUE IF NOT EXISTS 'manual'")
    op.execute("ALTER TYPE payment_method_enum ADD VALUE IF NOT EXISTS 'manual'")

    # ── 0013: Loyalty validation mode ─────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE loyalty_validation_mode_enum AS ENUM ('auto', 'manual');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        ALTER TABLE company_settings
            ADD COLUMN IF NOT EXISTS loyalty_validation_mode
                loyalty_validation_mode_enum NOT NULL DEFAULT 'auto'
    """)

    # ── 0014: Merchant API keys table ─────────────────────────────────────────
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
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_merchant_api_keys_key_hash
            ON merchant_api_keys(key_hash)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_merchant_api_keys_company_id
            ON merchant_api_keys(company_id)
    """)

    # ── 0015: Promotions table + orders columns ───────────────────────────────
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
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_promotions_company_active
            ON promotions(company_id, is_active)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_promotions_code
            ON promotions(company_id, code)
    """)
    op.execute("""
        ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS promotion_id UUID REFERENCES promotions(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS promotion_code VARCHAR(50)
    """)

    # ── 0016: Delivery zones table ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS delivery_zones (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            name VARCHAR(150) NOT NULL,
            description TEXT,
            delivery_fee_xof INTEGER NOT NULL DEFAULT 0,
            free_delivery_threshold_xof INTEGER,
            estimated_minutes INTEGER,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_delivery_zones_store ON delivery_zones(store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_delivery_zones_company ON delivery_zones(company_id)")

    # ── 0017: Payment refund fields ───────────────────────────────────────────
    op.execute("""
        ALTER TABLE payments
            ADD COLUMN IF NOT EXISTS refunded_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS refund_reason TEXT,
            ADD COLUMN IF NOT EXISTS refund_amount_xof INTEGER
    """)


def downgrade() -> None:
    # Irreversible safety migration — downgrade not supported
    pass
