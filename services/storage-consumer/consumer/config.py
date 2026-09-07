"""Storage-consumer configuration, read from environment variables.

Reuses the POSTGRES_* variables defined in the repo root .env / .env.example
(same convention as app-list-api-fastapi), plus the topic/consumer-group
names for the two broker topics this service consumes.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Loading the repo-root .env is a convenience for running this service
# outside of docker compose (e.g. from a local venv). Inside docker compose,
# environment variables are already injected and this file won't exist at
# this relative path, so it's a no-op there.
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
        self.stats_topic = os.getenv("PLAYSTORE_TOPIC", "playstore-app-stats")
        self.reviews_topic = os.getenv("PLAYSTORE_REVIEWS_TOPIC", "playstore-app-reviews")
        self.stats_group = os.getenv("STORAGE_CONSUMER_STATS_GROUP", "storage-consumer-stats")
        self.reviews_group = os.getenv("STORAGE_CONSUMER_REVIEWS_GROUP", "storage-consumer-reviews")
        # Distinguishes consumer processes within a group; group membership
        # (not this name) is what determines message distribution.
        self.consumer_name = os.getenv("HOSTNAME", "storage-consumer")


def get_config() -> Config:
    return Config()
