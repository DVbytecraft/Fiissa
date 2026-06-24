"""Loyalty engine + wallet payment methods

Revision ID: 0005_loyalty_wallet
Revises: 0004_customer_identity
Create Date: 2026-06-24 00:00:00.000000

Tables créées (9) :
  loyalty_programs, loyalty_tiers, card_templates,
  loyalty_cards, loyalty_transactions, loyalty_rewards,
  loyalty_coupons, customer_scores, wallet_payment_methods

Règles métier rappelées dans ce fichier :
  - loyalty_enabled = false par défaut (jamais auto-créé)
  - loyalty_transactions est append-only
  - wallet_payment_methods ne stocke que des références, jamais des fonds
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0005_loyalty_wallet"
down_revision = "0004_customer_identity"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_type(bind, name: str) -> bool:
    row = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": name}
    ).fetchone()
    return row is not None


def _create_enum_if_missing(bind, name: str, values: list[str]) -> None:
    if not _has_type(bind, name):
        enum_type = postgresql.ENUM(*values, name=name)
        enum_type.create(bind)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── Enums (idempotents) ───────────────────────────────────────────────────
    _create_enum_if_missing(bind, "loyalty_card_type_enum", ["native", "external"])
    _create_enum_if_missing(bind, "loyalty_card_status_enum", ["active", "suspended", "cancelled"])
    _create_enum_if_missing(bind, "loyalty_tx_type_enum", ["earn", "redeem", "bonus", "expire", "adjust"])
    _create_enum_if_missing(bind, "loyalty_reward_type_enum", ["discount_pct", "discount_fixed", "free_product", "gift"])
    _create_enum_if_missing(bind, "coupon_discount_type_enum", ["pct", "fixed"])
    _create_enum_if_missing(bind, "customer_segment_enum", ["new", "active", "loyal", "vip", "at_risk", "inactive"])
    _create_enum_if_missing(bind, "wallet_method_type_enum", ["mobile_money", "external_loyalty_card", "bank_card", "bank_account"])
    _create_enum_if_missing(bind, "wallet_operator_enum", ["wave", "orange_money", "free_money", "mtn_momo"])

    # ── loyalty_programs ──────────────────────────────────────────────────────
    if not _has_table(inspector, "loyalty_programs"):
        op.create_table(
            "loyalty_programs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("loyalty_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("points_per_xof", sa.Numeric(10, 4), nullable=False, server_default="0.01"),
            sa.Column("min_spend_xof", sa.Integer, nullable=False, server_default="0"),
            sa.Column("expiry_months", sa.Integer, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("company_id", "name", name="uq_loyalty_program_company_name"),
        )
        op.create_index("ix_loyalty_programs_company_id", "loyalty_programs", ["company_id"])

    # ── loyalty_tiers ─────────────────────────────────────────────────────────
    if not _has_table(inspector, "loyalty_tiers"):
        op.create_table(
            "loyalty_tiers",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("program_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("loyalty_programs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(60), nullable=False),
            sa.Column("min_points", sa.Integer, nullable=False, server_default="0"),
            sa.Column("multiplier", sa.Numeric(5, 2), nullable=False, server_default="1.0"),
            sa.Column("benefits", postgresql.JSONB, nullable=True),
            sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_loyalty_tiers_program_id", "loyalty_tiers", ["program_id"])
        op.create_index("ix_loyalty_tiers_company_id", "loyalty_tiers", ["company_id"])

    # ── card_templates ────────────────────────────────────────────────────────
    if not _has_table(inspector, "card_templates"):
        op.create_table(
            "card_templates",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tier_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("loyalty_tiers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("background_color", sa.String(7), nullable=False, server_default="#1A1A2E"),
            sa.Column("text_color", sa.String(7), nullable=False, server_default="#FFFFFF"),
            sa.Column("logo_url", sa.String(512), nullable=True),
            sa.Column("background_image_url", sa.String(512), nullable=True),
            sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_card_templates_company_id", "card_templates", ["company_id"])

    # ── loyalty_cards ─────────────────────────────────────────────────────────
    if not _has_table(inspector, "loyalty_cards"):
        op.create_table(
            "loyalty_cards",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("program_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("loyalty_programs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("tier_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("loyalty_tiers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("card_template_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("card_templates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("card_number", sa.String(32), nullable=False),
            sa.Column("points_balance", sa.Integer, nullable=False, server_default="0"),
            sa.Column("card_type",
                      postgresql.ENUM("native", "external", name="loyalty_card_type_enum", create_type=False),
                      nullable=False),
            sa.Column("external_issuer", sa.String(120), nullable=True),
            sa.Column("external_ref", sa.String(120), nullable=True),
            sa.Column("status",
                      postgresql.ENUM("active", "suspended", "cancelled", name="loyalty_card_status_enum", create_type=False),
                      nullable=False, server_default="active"),
            sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("company_id", "card_number", name="uq_loyalty_card_number_per_company"),
        )
        op.create_index("ix_loyalty_cards_company_id", "loyalty_cards", ["company_id"])
        op.create_index("ix_loyalty_cards_customer_id", "loyalty_cards", ["customer_id"])

    # ── loyalty_transactions ──────────────────────────────────────────────────
    if not _has_table(inspector, "loyalty_transactions"):
        op.create_table(
            "loyalty_transactions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("card_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("loyalty_cards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("type",
                      postgresql.ENUM("earn", "redeem", "bonus", "expire", "adjust",
                                      name="loyalty_tx_type_enum", create_type=False),
                      nullable=False),
            sa.Column("points_delta", sa.Integer, nullable=False),
            sa.Column("points_before", sa.Integer, nullable=False),
            sa.Column("points_after", sa.Integer, nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_loyalty_transactions_card_id", "loyalty_transactions", ["card_id"])
        op.create_index("ix_loyalty_transactions_customer_id", "loyalty_transactions", ["customer_id"])
        op.create_index("ix_loyalty_transactions_company_id", "loyalty_transactions", ["company_id"])

    # ── loyalty_rewards ───────────────────────────────────────────────────────
    if not _has_table(inspector, "loyalty_rewards"):
        op.create_table(
            "loyalty_rewards",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("program_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("loyalty_programs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("points_cost", sa.Integer, nullable=False),
            sa.Column("reward_type",
                      postgresql.ENUM("discount_pct", "discount_fixed", "free_product", "gift",
                                      name="loyalty_reward_type_enum", create_type=False),
                      nullable=False),
            sa.Column("value", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("max_redemptions", sa.Integer, nullable=True),
            sa.Column("redemptions_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_loyalty_rewards_program_id", "loyalty_rewards", ["program_id"])
        op.create_index("ix_loyalty_rewards_company_id", "loyalty_rewards", ["company_id"])

    # ── loyalty_coupons ───────────────────────────────────────────────────────
    if not _has_table(inspector, "loyalty_coupons"):
        op.create_table(
            "loyalty_coupons",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reward_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("loyalty_rewards.id", ondelete="SET NULL"), nullable=True),
            sa.Column("code", sa.String(32), nullable=False, unique=True),
            sa.Column("discount_type",
                      postgresql.ENUM("pct", "fixed", name="coupon_discount_type_enum", create_type=False),
                      nullable=False),
            sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
            sa.Column("min_order_xof", sa.Integer, nullable=False, server_default="0"),
            sa.Column("is_used", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("order_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_loyalty_coupons_customer_id", "loyalty_coupons", ["customer_id"])
        op.create_index("ix_loyalty_coupons_company_id", "loyalty_coupons", ["company_id"])

    # ── customer_scores ───────────────────────────────────────────────────────
    if not _has_table(inspector, "customer_scores"):
        op.create_table(
            "customer_scores",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("recency_score", sa.Integer, nullable=False, server_default="0"),
            sa.Column("frequency_score", sa.Integer, nullable=False, server_default="0"),
            sa.Column("monetary_score", sa.Integer, nullable=False, server_default="0"),
            sa.Column("rfm_score", sa.Integer, nullable=False, server_default="0"),
            sa.Column("segment",
                      postgresql.ENUM("new", "active", "loyal", "vip", "at_risk", "inactive",
                                      name="customer_segment_enum", create_type=False),
                      nullable=False, server_default="new"),
            sa.Column("last_order_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("order_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("total_spent_xof", sa.Integer, nullable=False, server_default="0"),
            sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("company_id", "customer_id", name="uq_customer_score_per_company"),
        )
        op.create_index("ix_customer_scores_company_id", "customer_scores", ["company_id"])
        op.create_index("ix_customer_scores_customer_id", "customer_scores", ["customer_id"])
        op.create_index("ix_customer_scores_company_segment", "customer_scores", ["company_id", "segment"])

    # ── wallet_payment_methods ────────────────────────────────────────────────
    if not _has_table(inspector, "wallet_payment_methods"):
        op.create_table(
            "wallet_payment_methods",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("method_type",
                      postgresql.ENUM("mobile_money", "external_loyalty_card", "bank_card", "bank_account",
                                      name="wallet_method_type_enum", create_type=False),
                      nullable=False),
            sa.Column("operator",
                      postgresql.ENUM("wave", "orange_money", "free_money", "mtn_momo",
                                      name="wallet_operator_enum", create_type=False),
                      nullable=True),
            sa.Column("phone_number", sa.String(20), nullable=True),
            sa.Column("display_name", sa.String(120), nullable=False),
            sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("metadata", postgresql.JSONB, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_wallet_payment_methods_customer_id", "wallet_payment_methods", ["customer_id"])
        op.create_index("ix_wallet_payment_methods_company_id", "wallet_payment_methods", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_wallet_payment_methods_company_id", table_name="wallet_payment_methods")
    op.drop_index("ix_wallet_payment_methods_customer_id", table_name="wallet_payment_methods")
    op.drop_table("wallet_payment_methods")

    op.drop_index("ix_customer_scores_company_segment", table_name="customer_scores")
    op.drop_index("ix_customer_scores_customer_id", table_name="customer_scores")
    op.drop_index("ix_customer_scores_company_id", table_name="customer_scores")
    op.drop_table("customer_scores")

    op.drop_index("ix_loyalty_coupons_company_id", table_name="loyalty_coupons")
    op.drop_index("ix_loyalty_coupons_customer_id", table_name="loyalty_coupons")
    op.drop_table("loyalty_coupons")

    op.drop_index("ix_loyalty_rewards_company_id", table_name="loyalty_rewards")
    op.drop_index("ix_loyalty_rewards_program_id", table_name="loyalty_rewards")
    op.drop_table("loyalty_rewards")

    op.drop_index("ix_loyalty_transactions_company_id", table_name="loyalty_transactions")
    op.drop_index("ix_loyalty_transactions_customer_id", table_name="loyalty_transactions")
    op.drop_index("ix_loyalty_transactions_card_id", table_name="loyalty_transactions")
    op.drop_table("loyalty_transactions")

    op.drop_index("ix_loyalty_cards_customer_id", table_name="loyalty_cards")
    op.drop_index("ix_loyalty_cards_company_id", table_name="loyalty_cards")
    op.drop_table("loyalty_cards")

    op.drop_index("ix_card_templates_company_id", table_name="card_templates")
    op.drop_table("card_templates")

    op.drop_index("ix_loyalty_tiers_company_id", table_name="loyalty_tiers")
    op.drop_index("ix_loyalty_tiers_program_id", table_name="loyalty_tiers")
    op.drop_table("loyalty_tiers")

    op.drop_index("ix_loyalty_programs_company_id", table_name="loyalty_programs")
    op.drop_table("loyalty_programs")

    # Drop enums
    bind = op.get_bind()
    for enum_name in [
        "wallet_operator_enum", "wallet_method_type_enum",
        "customer_segment_enum", "coupon_discount_type_enum",
        "loyalty_reward_type_enum", "loyalty_tx_type_enum",
        "loyalty_card_status_enum", "loyalty_card_type_enum",
    ]:
        bind.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
