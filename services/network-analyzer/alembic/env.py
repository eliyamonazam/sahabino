import asyncio
from logging.config import fileConfig

from alembic import context
from analyzer.config import get_database_url
from analyzer.database import Base
from analyzer.models import network_metrics  # noqa: F401  (registers the model on Base.metadata)
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The connection string comes from environment variables (see analyzer/config.py),
# never from a hardcoded value in this file or in alembic.ini.
config.set_main_option("sqlalchemy.url", get_database_url())

target_metadata = Base.metadata

# This service shares its Postgres database with app-list-api-fastapi and
# storage-consumer, which also use Alembic. Without a distinct version_table,
# all three services' Alembic histories would collide on the same default
# `alembic_version` table.
VERSION_TABLE = "alembic_version_network_analyzer"


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
