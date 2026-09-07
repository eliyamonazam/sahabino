import json
from typing import Any, AsyncIterator

import redis.asyncio as redis

from .base import BrokerMessage, MessageBroker


class RedisStreamsBroker(MessageBroker):
    """MessageBroker backed by Redis Streams (XADD / XREADGROUP / XACK)."""

    def __init__(self, host: str, port: int, block_ms: int = 5000) -> None:
        self._host = host
        self._port = port
        self._block_ms = block_ms
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        self._client = redis.Redis(host=self._host, port=self._port, decode_responses=True)
        await self._client.ping()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def _redis(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("RedisStreamsBroker.connect() must be called before use")
        return self._client

    async def publish(self, topic: str, payload: dict[str, Any]) -> str:
        return await self._redis.xadd(topic, {"payload": json.dumps(payload)})

    async def _ensure_group(self, topic: str, group: str) -> None:
        try:
            # id="0" replays the whole stream to a newly created group;
            # mkstream=True creates the stream itself if this is the first group on it.
            await self._redis.xgroup_create(topic, group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def consume(self, topic: str, group: str, consumer_name: str) -> AsyncIterator[BrokerMessage]:
        await self._ensure_group(topic, group)
        while True:
            response = await self._redis.xreadgroup(
                groupname=group,
                consumername=consumer_name,
                streams={topic: ">"},
                count=10,
                block=self._block_ms,
            )
            if not response:
                continue
            for _stream_name, entries in response:
                for entry_id, fields in entries:
                    yield BrokerMessage(id=entry_id, topic=topic, payload=json.loads(fields["payload"]))

    async def ack(self, topic: str, group: str, message: BrokerMessage) -> None:
        await self._redis.xack(topic, group, message.id)
