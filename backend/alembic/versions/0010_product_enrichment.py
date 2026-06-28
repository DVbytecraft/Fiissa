"""Product enrichment: brand, weight, dimensions, multi-images, attributes, tags, tax_rate, min/max_qty

Revision ID: 0010_product_enrichment
Revises: 0009_company_profile_pickup_delegation
Create Date: 2026-06-26
"""

from alembic import op

revision = "0010_product_enrichment"
down_revision = "0009_company_profile_pickup_delegation"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column("products", "max_order_qty")
    op.drop_column("products", "min_order_qty")
    op.drop_column("products", "tags")
    op.drop_column("products", "attributes")
    op.drop_column("products", "images")
    op.drop_column("products", "tax_rate")
    op.drop_column("products", "dimensions")
    op.drop_column("products", "volume_ml")
    op.drop_column("products", "weight_g")
    op.drop_column("products", "origin_country")
    op.drop_column("products", "brand")
