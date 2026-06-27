"""Product enrichment: brand, weight, dimensions, multi-images, attributes, tags, tax_rate, min/max_qty

Revision ID: 0010_product_enrichment
Revises: 0009_company_profile_pickup_delegation
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010_product_enrichment"
down_revision = "0009_company_profile_pickup_delegation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Identité produit ──────────────────────────────────────────────────────
    op.add_column("products", sa.Column("brand", sa.String(200), nullable=True))
    op.add_column("products", sa.Column("origin_country", sa.String(100), nullable=True))

    # ── Poids / volume / dimensions physiques ────────────────────────────────
    op.add_column("products", sa.Column("weight_g", sa.Integer(), nullable=True,
                                        comment="Poids net en grammes (ex: 1000 pour 1 kg)"))
    op.add_column("products", sa.Column("volume_ml", sa.Integer(), nullable=True,
                                        comment="Volume en millilitres (ex: 1000 pour 1 L)"))
    op.add_column("products", sa.Column("dimensions", JSONB, nullable=True,
                                        comment='{"length_cm": 10, "width_cm": 5, "height_cm": 3}'))

    # ── Prix et fiscalité ────────────────────────────────────────────────────
    op.add_column("products", sa.Column("tax_rate", sa.Integer(), nullable=True,
                                        comment="Taux TVA en % entier (ex: 18 pour 18%). NULL = taux par défaut"))

    # ── Images multiples ─────────────────────────────────────────────────────
    op.add_column("products", sa.Column("images", JSONB, nullable=True,
                                        comment='["https://cdn/.../img2.jpg", "https://cdn/.../img3.jpg"]'))

    # ── Attributs libres et tags ─────────────────────────────────────────────
    op.add_column("products", sa.Column("attributes", JSONB, nullable=True,
                                        comment='{"couleur": "rouge", "taille": "XL", "saveur": "vanille"}'))
    op.add_column("products", sa.Column("tags", JSONB, nullable=True,
                                        comment='["bio", "halal", "sans-gluten", "promo", "nouveaute"]'))

    # ── Quantités min/max commande ───────────────────────────────────────────
    op.add_column("products", sa.Column("min_order_qty", sa.Integer(), nullable=False,
                                        server_default="1"))
    op.add_column("products", sa.Column("max_order_qty", sa.Integer(), nullable=True))


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
