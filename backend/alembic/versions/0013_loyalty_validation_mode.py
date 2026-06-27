"""Add loyalty_validation_mode to company_settings

Revision ID: 0013_loyalty_validation_mode
Revises: 0012_add_togo_operators
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_loyalty_validation_mode"
down_revision = "0012_add_togo_operators"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE loyalty_validation_mode_enum AS ENUM ('auto', 'manual')")

    op.add_column(
        "company_settings",
        sa.Column(
            "loyalty_validation_mode",
            sa.Enum("auto", "manual", name="loyalty_validation_mode_enum", create_type=False),
            nullable=False,
            server_default="auto",
        ),
    )


def downgrade() -> None:
    op.drop_column("company_settings", "loyalty_validation_mode")
    op.execute("DROP TYPE loyalty_validation_mode_enum")
