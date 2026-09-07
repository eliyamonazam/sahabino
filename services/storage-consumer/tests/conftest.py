import os

import pytest
import pytest_asyncio
from consumer.config import build_database_url
from consumer.database import Base
from consumer.models import review, stats  # noqa: F401  (registers the models on Base.metadata)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = build_database_url(
    os.getenv("POSTGRES_TEST_DB_STORAGE_CONSUMER", "sahabino_test_storage_consumer")
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    # NullPool: a fresh asyncpg connection per checkout, since each test
    # function gets its own event loop under pytest-asyncio's default
    # (function-scoped) loop policy, and asyncpg connections can't be
    # reused across event loops.
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(engine):
    yield
    async with engine.begin() as conn:
        await conn.execute(Base.metadata.tables["reviews"].delete())
        await conn.execute(Base.metadata.tables["app_stats_snapshots"].delete())


@pytest.fixture
def anyio_backend():
    return "asyncio"
