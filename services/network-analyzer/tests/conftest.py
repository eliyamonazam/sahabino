import os
from pathlib import Path

import pytest
import pytest_asyncio
from analyzer.config import build_database_url
from analyzer.database import Base
from analyzer.models import network_metrics  # noqa: F401  (registers the model on Base.metadata)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = build_database_url(
    os.getenv("POSTGRES_TEST_DB_NETWORK_ANALYZER", "sahabino_test_network_analyzer")
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PCAP = FIXTURES_DIR / "sample.pcap"
MULTI_STREAM_HANDSHAKES_PCAP = FIXTURES_DIR / "multi_stream_handshakes.pcap"


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
        await conn.execute(Base.metadata.tables["network_metrics"].delete())


@pytest.fixture
def anyio_backend():
    return "asyncio"
