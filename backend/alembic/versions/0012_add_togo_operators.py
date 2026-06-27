"""Add Togo operators (tmoney, flooz) and manual method to payment enums

Revision ID: 0012_add_togo_operators
Revises: 0011_account_lockout
Create Date: 2026-06-28
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0012_add_togo_operators"
down_revision = "0011_account_lockout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter les nouvelles valeurs d'opérateurs pour le Togo et le mode manuel
    op.execute("ALTER TYPE payment_operator_enum ADD VALUE IF NOT EXISTS 'tmoney'")
    op.execute("ALTER TYPE payment_operator_enum ADD VALUE IF NOT EXISTS 'flooz'")
    op.execute("ALTER TYPE payment_operator_enum ADD VALUE IF NOT EXISTS 'manual'")
    
    # Ajouter la méthode 'manual'
    op.execute("ALTER TYPE payment_method_enum ADD VALUE IF NOT EXISTS 'manual'")


def downgrade() -> None:
    # PostgreSQL ne supporte pas le retrait direct d'une valeur d'ENUM.
    # Il faudrait recréer l'ENUM sans ces valeurs, ce qui est lourd et non nécessaire en pratique.
    pass