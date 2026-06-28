import asyncio
from logging.config import fileConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import tous les modèles pour que Alembic les détecte
from core.database import Base
from core.config import settings

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

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Ensure alembic_version table exists with wide enough version_num column.
        # Our revision IDs (e.g. "0018_fix_missing_columns") exceed the default 32 chars.
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version"
            " (version_num VARCHAR(255) NOT NULL,"
            "  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        ))
        await conn.execute(text(
            "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
        ))
        await conn.commit()

        await conn.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
