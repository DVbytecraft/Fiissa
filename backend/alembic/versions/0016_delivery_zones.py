"""0016 — Zones de livraison par magasin

Revision ID: 0016_delivery_zones
Revises: 0015_promotions
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0016_delivery_zones"
down_revision = "0015_promotions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("store_id", UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("delivery_fee_xof", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("free_delivery_threshold_xof", sa.Integer, nullable=True),
        sa.Column("estimated_minutes", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_delivery_zones_store", "delivery_zones", ["store_id"])
    op.create_index("ix_delivery_zones_company", "delivery_zones", ["company_id"])


def downgrade() -> None:
    op.drop_table("delivery_zones")
