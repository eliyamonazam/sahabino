import os
import uuid

import pytest


@pytest.fixture
def redis_connection_kwargs() -> dict:
    return {
        "host": os.environ.get("REDIS_HOST", "localhost"),
        "port": int(os.environ.get("REDIS_PORT", "6379")),
    }


@pytest.fixture
def kafka_bootstrap_servers() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


@pytest.fixture
def topic() -> str:
    # A fresh topic/stream per test avoids interference from prior test runs' data.
    return f"test-topic-{uuid.uuid4().hex[:8]}"
