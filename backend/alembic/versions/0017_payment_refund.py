"""0017 — Champs de remboursement sur les paiements

Revision ID: 0017_payment_refund
Revises: 0016_delivery_zones
Create Date: 2026-06-27
"""

from alembic import op

revision = "0017_payment_refund"
down_revision = "0016_delivery_zones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE payments
            ADD COLUMN IF NOT EXISTS refunded_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS refund_reason TEXT,
            ADD COLUMN IF NOT EXISTS refund_amount_xof INTEGER
    """)


def downgrade() -> None:
    op.drop_column("payments", "refund_amount_xof")
    op.drop_column("payments", "refund_reason")
    op.drop_column("payments", "refunded_at")
    op.drop_column("payments", "refunded_by_id")
