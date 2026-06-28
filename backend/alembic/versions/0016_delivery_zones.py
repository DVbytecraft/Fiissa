"""0016 — Zones de livraison par magasin

Revision ID: 0016_delivery_zones
Revises: 0015_promotions
Create Date: 2026-06-27
"""

from alembic import op

revision = "0016_delivery_zones"
down_revision = "0015_promotions"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_table("delivery_zones")
