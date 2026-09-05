import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import build_database_url
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = build_database_url(os.getenv("POSTGRES_TEST_DB", "sahabino_test"))


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
        await conn.execute(Base.metadata.tables["apps"].delete())


@pytest_asyncio.fixture
async def client(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
