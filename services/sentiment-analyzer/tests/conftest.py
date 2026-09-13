import os

import pytest
import pytest_asyncio
from sentiment.config import build_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = build_database_url(
    os.getenv("POSTGRES_TEST_DB_SENTIMENT_ANALYZER", "sahabino_test_sentiment_analyzer")
)

# This service doesn't own the `reviews` table's schema (storage-consumer's
# Alembic history does) and runs no migrations of its own -- this DDL is
# copied by hand from
# services/storage-consumer/alembic/versions/72bc1a63a7b8_create_app_stats_snapshots_and_reviews_.py
# (the `reviews` table only) and must be kept in sync manually if that
# migration ever changes. Same pattern as app-list-api-django's conftest.py
# for the `apps` table it likewise doesn't own.
CREATE_REVIEWS_TABLE_SQL = """
CREATE TABLE reviews (
    review_id VARCHAR(255) PRIMARY KEY,
    app_id INTEGER NOT NULL,
    at TIMESTAMPTZ,
    user_name VARCHAR(255),
    thumbs_up_count INTEGER,
    score INTEGER,
    content TEXT,
    sentiment VARCHAR(50),
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL
);
"""

DROP_REVIEWS_TABLE_SQL = "DROP TABLE IF EXISTS reviews;"


@pytest_asyncio.fixture(scope="session")
async def engine():
    # NullPool: a fresh asyncpg connection per checkout, since each test
    # function gets its own event loop under pytest-asyncio's default
    # (function-scoped) loop policy, and asyncpg connections can't be
    # reused across event loops.
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text(DROP_REVIEWS_TABLE_SQL))
        await conn.execute(text(CREATE_REVIEWS_TABLE_SQL))
    yield engine
    async with engine.begin() as conn:
        await conn.execute(text(DROP_REVIEWS_TABLE_SQL))
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _clean_table(engine):
    yield
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM reviews"))


@pytest.fixture
def anyio_backend():
    return "asyncio"
