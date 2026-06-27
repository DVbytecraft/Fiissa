"""0015 — Système de promotions / codes promo

Revision ID: 0015_promotions
Revises: 0014_merchant_api_keys
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0015_promotions"
down_revision = "0014_merchant_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE promotion_type_enum AS ENUM ('percentage', 'fixed', 'bogo')")
    op.execute("CREATE TYPE promotion_applies_to_enum AS ENUM ('all', 'category', 'product')")

    op.create_table(
        "promotions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("type", sa.Enum("percentage", "fixed", "bogo", name="promotion_type_enum", create_type=False), nullable=False),
        sa.Column("value", sa.Integer, nullable=False),
        sa.Column("applies_to", sa.Enum("all", "category", "product", name="promotion_applies_to_enum", create_type=False), nullable=False, server_default="all"),
        sa.Column("target_ids", JSONB, nullable=True),
        sa.Column("min_order_xof", sa.Integer, nullable=True),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("uses_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("start_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("end_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("stackable", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_promotions_company_active", "promotions", ["company_id", "is_active"])
    op.create_index("ix_promotions_code", "promotions", ["company_id", "code"], unique=True)

    # Lier la promotion appliquée à une commande
    op.add_column("orders", sa.Column(
        "promotion_id", UUID(as_uuid=True),
        sa.ForeignKey("promotions.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("orders", sa.Column("promotion_code", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "promotion_code")
    op.drop_column("orders", "promotion_id")
    op.drop_index("ix_promotions_code", table_name="promotions")
    op.drop_index("ix_promotions_company_active", table_name="promotions")
    op.drop_table("promotions")
    op.execute("DROP TYPE IF EXISTS promotion_type_enum")
    op.execute("DROP TYPE IF EXISTS promotion_applies_to_enum")
