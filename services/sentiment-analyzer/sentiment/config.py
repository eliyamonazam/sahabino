"""sentiment-analyzer configuration, read from environment variables.

Reuses conventions from the other services: load the repo-root .env as a
convenience for running outside docker compose, where it's already a no-op
since environment variables are injected directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_parents = Path(__file__).resolve().parents
if len(_parents) > 3 and (_parents[3] / ".env").exists():
    load_dotenv(_parents[3] / ".env")


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def build_database_url(db_name: str | None = None) -> str:
    """Build an asyncpg SQLAlchemy URL from the POSTGRES_* environment variables.

    Pass db_name to target a different database on the same Postgres instance
    (used by the test suite to point at a separate test database).
    """
    user = _env("POSTGRES_USER", "sahabino")
    password = _env("POSTGRES_PASSWORD", "changeme")
    host = _env("POSTGRES_HOST", "localhost")
    port = _env("POSTGRES_PORT", "5432")
    db = db_name or _env("POSTGRES_DB", "sahabino")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or build_database_url()


class Config:
    def __init__(self) -> None:
        # How many `sentiment IS NULL` rows to fetch, classify, and commit per
        # round trip. Keeps memory bounded on the ~17k-row reviews table (and
        # whatever it grows to) instead of loading every unscored row at once.
        self.batch_size = int(os.getenv("SENTIMENT_BATCH_SIZE", "500"))


def get_config() -> Config:
    return Config()
