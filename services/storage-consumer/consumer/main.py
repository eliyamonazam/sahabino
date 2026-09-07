import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from consumer.config import get_config
from consumer.database import build_session_factory
from consumer.parsing import parse_review_message, parse_stats_message
from consumer.persistence import insert_stats_snapshot, upsert_review
from message_broker import get_broker
from message_broker.base import BrokerMessage, MessageBroker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("storage-consumer")


async def _handle_stats_message(session_factory: async_sessionmaker, payload: dict) -> None:
    stats = parse_stats_message(payload)
    async with session_factory() as session:
        await insert_stats_snapshot(session, stats)


async def _handle_review_message(session_factory: async_sessionmaker, payload: dict) -> None:
    review = parse_review_message(payload)
    async with session_factory() as session:
        await upsert_review(session, review)


async def _run_consumer_loop(
    messages: AsyncIterator[BrokerMessage],
    handle_payload: Callable[[dict], Awaitable[None]],
    ack: Callable[[BrokerMessage], Awaitable[None]],
    label: str,
) -> None:
    """Process messages one at a time, acking only on success.

    A message that fails to process (bad data, DB error) is logged and
    skipped rather than crashing the loop; it is left unacked so the broker
    redelivers it instead of silently dropping it.
    """
    async for message in messages:
        try:
            await handle_payload(message.payload)
        except Exception:
            logger.exception("Failed to process %s message %s, skipping", label, message.id)
            continue
        await ack(message)


async def _consume_topic(
    broker: MessageBroker,
    topic: str,
    group: str,
    consumer_name: str,
    handle_payload: Callable[[dict], Awaitable[None]],
    label: str,
) -> None:
    messages = broker.consume(topic, group, consumer_name)

    async def ack(message: BrokerMessage) -> None:
        await broker.ack(topic, group, message)

    await _run_consumer_loop(messages, handle_payload, ack, label)


async def main() -> None:
    config = get_config()
    session_factory = build_session_factory()

    async def handle_stats(payload: dict) -> None:
        await _handle_stats_message(session_factory, payload)

    async def handle_reviews(payload: dict) -> None:
        await _handle_review_message(session_factory, payload)

    async with get_broker() as broker:
        logger.info(
            "Consuming %s (group=%s) and %s (group=%s)",
            config.stats_topic,
            config.stats_group,
            config.reviews_topic,
            config.reviews_group,
        )
        await asyncio.gather(
            _consume_topic(
                broker, config.stats_topic, config.stats_group, config.consumer_name, handle_stats, "stats"
            ),
            _consume_topic(
                broker,
                config.reviews_topic,
                config.reviews_group,
                config.consumer_name,
                handle_reviews,
                "reviews",
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
