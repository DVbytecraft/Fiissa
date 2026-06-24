"""Production hardening — document_sequences + subscription columns

Revision ID: 0003_production_hardening
Revises: 0002_platform_extensions
Create Date: 2026-06-24 00:00:00.000000

Changes:
  - document_sequences : numérotation atomique (SC-, PAY-, REC-, INV-)
  - subscriptions      : colonnes billing_cycle, amount_xof, trial_ends_at,
                         current_period_start, current_period_end, cancelled_at
  - subscription_invoices : index company_id + subscription_id
  - subscription_renewals : index company_id + subscription_id
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0003_production_hardening"
down_revision = "0002_platform_extensions"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(name: str, table_name: str, columns: list[str], unique: bool = False) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if name not in existing:
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── document_sequences ─────────────────────────────────────────────────────
    # Compteur atomique par (company_id, doc_type, year) — utilisé par core/sequences.py
    # pour générer SC-2026-00042, PAY-2026-00001, REC-2026-00007, INV-2026-00001
    if not _has_table(inspector, "document_sequences"):
        op.create_table(
            "document_sequences",
            sa.Column(
                "company_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("companies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("doc_type", sa.String(20), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("company_id", "doc_type", "year"),
        )
        op.create_index(
            "ix_document_sequences_company_doc_year",
            "document_sequences",
            ["company_id", "doc_type", "year"],
            unique=True,
        )

    # ── subscriptions : colonnes ORM absentes du schéma DB ────────────────────
    for col in (
        sa.Column("billing_cycle", sa.String(20), nullable=True, server_default="monthly"),
        sa.Column("amount_xof", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    ):
        _add_column_if_missing("subscriptions", col)

    # Rétro-remplir current_period_start / current_period_end depuis starts_at / ends_at
    # (colonnes présentes dans migration 0001)
    op.execute(
        """
        UPDATE subscriptions
        SET current_period_start = starts_at
        WHERE current_period_start IS NULL
          AND starts_at IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE subscriptions
        SET current_period_end = ends_at
        WHERE current_period_end IS NULL
          AND ends_at IS NOT NULL
        """
    )

    # ── subscription_invoices : index pour performances ────────────────────────
    _create_index_if_missing(
        "ix_subscription_invoices_company_id",
        "subscription_invoices",
        ["company_id"],
    )
    _create_index_if_missing(
        "ix_subscription_invoices_subscription_id",
        "subscription_invoices",
        ["subscription_id"],
    )

    # ── subscription_renewals : index pour performances ────────────────────────
    _create_index_if_missing(
        "ix_subscription_renewals_company_id",
        "subscription_renewals",
        ["company_id"],
    )
    _create_index_if_missing(
        "ix_subscription_renewals_subscription_id",
        "subscription_renewals",
        ["subscription_id"],
    )

    # ── payments : index company_id pour requêtes multi-tenant ────────────────
    _create_index_if_missing(
        "ix_payments_company_id",
        "payments",
        ["company_id"],
    )

    # ── receipts : index company_id ───────────────────────────────────────────
    _create_index_if_missing(
        "ix_receipts_company_id",
        "receipts",
        ["company_id"],
    )

    # ── orders : index company_id (si manquant) ────────────────────────────────
    _create_index_if_missing(
        "ix_orders_company_id",
        "orders",
        ["company_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_table(inspector, "document_sequences"):
        op.drop_table("document_sequences")

    for col_name in (
        "billing_cycle",
        "amount_xof",
        "trial_ends_at",
        "current_period_start",
        "current_period_end",
        "cancelled_at",
    ):
        if _has_column(inspector, "subscriptions", col_name):
            op.drop_column("subscriptions", col_name)
