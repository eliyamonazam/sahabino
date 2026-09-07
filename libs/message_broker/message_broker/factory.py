import os

from .base import MessageBroker
from .kafka_broker import KafkaBroker
from .redis_broker import RedisStreamsBroker


def get_broker(broker_type: str | None = None) -> MessageBroker:
    """Build a MessageBroker from an explicit type or the MESSAGE_BROKER_TYPE env var.

    Connection settings always come from the environment, so callers only
    need to choose the backend (or let the environment choose it for them).
    """
    resolved_type = (broker_type or os.environ.get("MESSAGE_BROKER_TYPE", "redis")).lower()

    if resolved_type == "redis":
        return RedisStreamsBroker(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
        )
    if resolved_type == "kafka":
        return KafkaBroker(
            bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        )
    raise ValueError(f"Unknown MESSAGE_BROKER_TYPE: {resolved_type!r} (expected 'redis' or 'kafka')")
