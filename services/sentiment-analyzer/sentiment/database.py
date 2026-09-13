from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from sentiment.config import get_database_url


class Base(DeclarativeBase):
    pass


def build_session_factory(database_url: str | None = None) -> async_sessionmaker:
    """Build a session factory against database_url, or the default DB if omitted.

    Kept as a factory function (rather than a module-level engine) so tests
    can point it at a separate test database.
    """
    engine: AsyncEngine = create_async_engine(database_url or get_database_url(), pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)
