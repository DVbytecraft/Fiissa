"""Add loyalty_validation_mode to company_settings

Revision ID: 0013_loyalty_validation_mode
Revises: 0012_add_togo_operators
Create Date: 2026-06-27
"""

from alembic import op


revision = "0013_loyalty_validation_mode"
down_revision = "0012_add_togo_operators"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column("company_settings", "loyalty_validation_mode")
    op.execute("DROP TYPE loyalty_validation_mode_enum")
