"""Exercises _run_consumer_loop's error handling directly, feeding it
BrokerMessage objects built by hand instead of a real broker connection --
what matters here is the loop's own control flow (skip-and-continue on a
bad message, ack only on success), not the broker abstraction itself, which
already has its own integration tests in libs/message_broker.
"""

from collections.abc import AsyncIterator

from consumer.main import _handle_review_message, _handle_stats_message, _run_consumer_loop
from consumer.models.review import Review
from consumer.models.stats import AppStatsSnapshot
from sqlalchemy import select

from message_broker.base import BrokerMessage


async def _as_messages(topic: str, payloads: list[dict]) -> AsyncIterator[BrokerMessage]:
    for i, payload in enumerate(payloads):
        yield BrokerMessage(id=str(i), topic=topic, payload=payload)


async def test_malformed_stats_message_is_skipped_without_blocking_valid_ones(session_factory):
    payloads = [
        {"app_id": 1, "scraped_at": "2026-09-07T10:00:00+00:00", "score": 4.1},  # valid
        {"score": 4.9},  # malformed: missing app_id
        {"app_id": 2, "scraped_at": "2026-09-07T10:05:00+00:00", "score": 4.2},  # valid
    ]
    acked_ids = []

    async def handle(payload: dict) -> None:
        await _handle_stats_message(session_factory, payload)

    async def ack(message: BrokerMessage) -> None:
        acked_ids.append(message.id)

    await _run_consumer_loop(_as_messages("playstore-app-stats", payloads), handle, ack, "stats")

    async with session_factory() as session:
        rows = (await session.execute(select(AppStatsSnapshot))).scalars().all()

    assert {row.app_id for row in rows} == {1, 2}
    assert acked_ids == ["0", "2"]


async def test_malformed_review_message_is_skipped_without_blocking_valid_ones(session_factory):
    payloads = [
        {"review_id": "r1", "app_id": 1, "content": "good"},  # valid
        {"content": "no ids at all"},  # malformed: missing review_id and app_id
        {"review_id": "r2", "app_id": 1, "content": "also good"},  # valid
    ]
    acked_ids = []

    async def handle(payload: dict) -> None:
        await _handle_review_message(session_factory, payload)

    async def ack(message: BrokerMessage) -> None:
        acked_ids.append(message.id)

    await _run_consumer_loop(_as_messages("playstore-app-reviews", payloads), handle, ack, "reviews")

    async with session_factory() as session:
        rows = (await session.execute(select(Review))).scalars().all()

    assert {row.review_id for row in rows} == {"r1", "r2"}
    assert acked_ids == ["0", "2"]
