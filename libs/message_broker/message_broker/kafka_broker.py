import json
from typing import Any, AsyncIterator

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import TopicPartition

from .base import BrokerMessage, MessageBroker


class KafkaBroker(MessageBroker):
    """MessageBroker backed by Kafka, via aiokafka.

    Consumers commit offsets manually (enable_auto_commit=False) so ack()
    controls exactly when a message is considered processed, matching the
    Redis Streams implementation's explicit-ack semantics.
    """

    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None
        self._consumers: dict[tuple[str, str], AIOKafkaConsumer] = {}

    async def connect(self) -> None:
        self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap_servers)
        await self._producer.start()

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
        for consumer in self._consumers.values():
            await consumer.stop()
        self._consumers.clear()

    @property
    def _producer_or_raise(self) -> AIOKafkaProducer:
        if self._producer is None:
            raise RuntimeError("KafkaBroker.connect() must be called before use")
        return self._producer

    async def publish(self, topic: str, payload: dict[str, Any]) -> str:
        record = await self._producer_or_raise.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
        return f"{record.partition}-{record.offset}"

    async def consume(self, topic: str, group: str, consumer_name: str) -> AsyncIterator[BrokerMessage]:
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=group,
            client_id=consumer_name,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        await consumer.start()
        self._consumers[(topic, group)] = consumer
        try:
            async for record in consumer:
                payload = json.loads(record.value.decode("utf-8"))
                yield BrokerMessage(id=f"{record.partition}-{record.offset}", topic=topic, payload=payload)
        finally:
            await consumer.stop()
            self._consumers.pop((topic, group), None)

    async def ack(self, topic: str, group: str, message: BrokerMessage) -> None:
        consumer = self._consumers.get((topic, group))
        if consumer is None:
            raise RuntimeError(f"No active consumer for topic={topic!r} group={group!r}; consume() first")
        partition_str, offset_str = message.id.split("-")
        tp = TopicPartition(topic, int(partition_str))
        # Committed offset is "next offset to read", hence +1.
        await consumer.commit({tp: int(offset_str) + 1})
