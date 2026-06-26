"""Company public profile + pickup delegation (procuration / coursier)

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009_company_profile_pickup_delegation"
down_revision = "0008_postgres_enum_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Profil public entreprise ──────────────────────────────────────────────
    op.add_column("companies", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("website_url", sa.String(512), nullable=True))
    op.add_column("companies", sa.Column("opening_hours", JSONB, nullable=True,
                                         comment="{'mon':{'open':'08:00','close':'20:00','closed':false}, ...}"))

    # ── Pickup — méthode de retrait & délégation ──────────────────────────────
    op.execute(
        "ALTER TYPE pickup_status_enum ADD VALUE IF NOT EXISTS 'cancelled'"
    )

    fulfillment_enum = sa.Enum(
        "self_pickup", "delegate", "company_delivery", "own_courier",
        name="pickup_fulfillment_enum",
    )
    fulfillment_enum.create(op.get_bind(), checkfirst=True)

    id_type_enum = sa.Enum(
        "carte_identite", "passeport", "permis", "photo",
        name="delegate_id_type_enum",
    )
    id_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("pickups", sa.Column(
        "fulfillment_method",
        sa.Enum("self_pickup", "delegate", "company_delivery", "own_courier",
                name="pickup_fulfillment_enum"),
        nullable=False,
        server_default="self_pickup",
    ))
    op.add_column("pickups", sa.Column("delegate_first_name", sa.String(100), nullable=True))
    op.add_column("pickups", sa.Column("delegate_last_name", sa.String(100), nullable=True))
    op.add_column("pickups", sa.Column(
        "delegate_id_type",
        sa.Enum("carte_identite", "passeport", "permis", "photo",
                name="delegate_id_type_enum"),
        nullable=True,
    ))
    op.add_column("pickups", sa.Column("delegate_id_url", sa.Text(), nullable=True,
                                        comment="URL de la pièce d'identité ou photo uploadée"))
    op.add_column("pickups", sa.Column("delegate_message", sa.Text(), nullable=True,
                                        comment="Message pré-rédigé pour le personnel de l'enseigne"))
    op.add_column("pickups", sa.Column("courier_info", JSONB, nullable=True,
                                        comment="Infos coursier: {name, id_number, phone, photo_url}"))
    op.add_column("pickups", sa.Column("delivery_address", JSONB, nullable=True,
                                        comment="Adresse de livraison quand fulfillment=company_delivery"))
    op.add_column("pickups", sa.Column("delivery_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pickups", "delivery_notes")
    op.drop_column("pickups", "delivery_address")
    op.drop_column("pickups", "courier_info")
    op.drop_column("pickups", "delegate_message")
    op.drop_column("pickups", "delegate_id_url")
    op.drop_column("pickups", "delegate_id_type")
    op.drop_column("pickups", "delegate_last_name")
    op.drop_column("pickups", "delegate_first_name")
    op.drop_column("pickups", "fulfillment_method")

    op.drop_column("companies", "opening_hours")
    op.drop_column("companies", "website_url")
    op.drop_column("companies", "description")
