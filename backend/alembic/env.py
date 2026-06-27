from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Import tous les modèles pour que Alembic les détecte
from core.database import Base
from core.config import settings

# Importer tous les modèles
import apps.users.models  # noqa
import apps.companies.models  # noqa
import apps.stores.models  # noqa
import apps.catalog.models  # noqa
import apps.orders.models  # noqa
import apps.payments.models  # noqa
import apps.receipts.models  # noqa
import apps.notifications.models  # noqa
import apps.integrations.models  # noqa
import apps.loyalty.models  # noqa
import apps.wallet.models  # noqa
import apps.promotions.models  # noqa
import apps.support.models  # noqa

config = context.config

# Use the sync URL (psycopg2) for Alembic migrations — more reliable than async.
# The app itself uses postgresql+asyncpg:// at runtime.
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # sslmode=disable avoids psycopg2 SSL-handshake hang on Render internal network.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"sslmode": "disable"},
    )

    # Alembic creates alembic_version with version_num VARCHAR(32) by default.
    # Our revision IDs (e.g. "0007_merchant_onboarding_idempotency") exceed 32 chars,
    # so we pre-create or widen the column to VARCHAR(255) before running migrations.
    with connectable.connect() as pre_conn:
        pre_conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version"
            " (version_num VARCHAR(255) NOT NULL,"
            " CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        ))
        pre_conn.execute(text(
            "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
        ))
        pre_conn.commit()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
