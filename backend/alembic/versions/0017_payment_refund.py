"""0017 — Champs de remboursement sur les paiements

Revision ID: 0017_payment_refund
Revises: 0016_delivery_zones
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0017_payment_refund"
down_revision = "0016_delivery_zones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column(
        "refunded_by_id", UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    ))
    op.add_column("payments", sa.Column(
        "refunded_at", sa.TIMESTAMP(timezone=True), nullable=True,
    ))
    op.add_column("payments", sa.Column(
        "refund_reason", sa.Text, nullable=True,
    ))
    op.add_column("payments", sa.Column(
        "refund_amount_xof", sa.Integer, nullable=True,
    ))


def downgrade() -> None:
    op.drop_column("payments", "refund_amount_xof")
    op.drop_column("payments", "refund_reason")
    op.drop_column("payments", "refunded_at")
    op.drop_column("payments", "refunded_by_id")
