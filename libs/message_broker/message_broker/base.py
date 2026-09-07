from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class BrokerMessage:
    """A message read back from a broker, plus enough to acknowledge it."""

    id: str
    topic: str
    payload: dict[str, Any]


class MessageBroker(ABC):
    """Common publish/consume interface over a Redis Streams or Kafka backend.

    Both backends deliver via named consumer groups, so multiple consumer
    processes can share a topic's workload, and both require an explicit
    ack() once a message has been durably processed — this is at-least-once
    delivery, not at-most-once, so consumers must tolerate redelivery.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Open the underlying broker connection."""

    @abstractmethod
    async def close(self) -> None:
        """Close the underlying broker connection."""

    @abstractmethod
    async def publish(self, topic: str, payload: dict[str, Any]) -> str:
        """Publish payload to topic, returning the broker-assigned message id."""

    @abstractmethod
    def consume(self, topic: str, group: str, consumer_name: str) -> AsyncIterator[BrokerMessage]:
        """Yield messages published to topic for the given consumer group.

        Iterate with `async for message in broker.consume(...)`; it runs
        until the broker connection is closed.
        """

    @abstractmethod
    async def ack(self, topic: str, group: str, message: BrokerMessage) -> None:
        """Acknowledge a message as processed so it won't be redelivered."""

    async def __aenter__(self) -> "MessageBroker":
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
