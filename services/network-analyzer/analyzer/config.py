"""network-analyzer configuration, read from environment variables.

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
        self.app_list_api_url = os.getenv("APP_LIST_API_URL", "http://app-list-api-fastapi:8000")
        # Directory scanned for .pcap files when none is given on the command
        # line. Relative paths are resolved against the current working
        # directory the process was started from (the repo root, both
        # locally and in the container - see the Dockerfile/docker-compose.yml).
        self.pcap_dir = os.getenv("PCAP_DIR", "data/pcap-samples")


def get_config() -> Config:
    return Config()
