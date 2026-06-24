"""Customer identity extension

Revision ID: 0004_customer_identity
Revises: 0003_production_hardening
Create Date: 2026-06-24 00:00:00.000000

Changes:
  - users : email_verified, phone_verified, preferred_language, marketing_opt_in
  - email_verification_tokens : tokens usage-unique pour vérification email
  - password_reset_tokens     : tokens usage-unique pour réinitialisation mdp
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0004_customer_identity"
down_revision = "0003_production_hardening"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, col_name: str) -> bool:
    return col_name in {c["name"] for c in inspector.get_columns(table_name)}


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return index_name in {i["name"] for i in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── users : champs identité étendue ────────────────────────────────────────
    for col in (
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("preferred_language", sa.String(10), nullable=False, server_default="fr"),
        sa.Column("marketing_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    ):
        if not _has_column(inspector, "users", col.name):
            op.add_column("users", col)

    # ── email_verification_tokens ──────────────────────────────────────────────
    if not _has_table(inspector, "email_verification_tokens"):
        op.create_table(
            "email_verification_tokens",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "is_used",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_email_verification_tokens_user_id",
            "email_verification_tokens",
            ["user_id"],
        )

    # ── password_reset_tokens ──────────────────────────────────────────────────
    if not _has_table(inspector, "password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "is_used",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_password_reset_tokens_user_id",
            "password_reset_tokens",
            ["user_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "marketing_opt_in")
    op.drop_column("users", "preferred_language")
    op.drop_column("users", "phone_verified")
    op.drop_column("users", "email_verified")
