from datetime import UTC, datetime

import pytest
from consumer.models.review import Review
from consumer.models.stats import AppStatsSnapshot
from consumer.parsing import InvalidMessageError, parse_review_message, parse_stats_message
from consumer.persistence import insert_stats_snapshot, upsert_review
from sqlalchemy import select


def make_stats_payload(**overrides) -> dict:
    payload = {
        "app_id": 1,
        "package_name": "com.whatsapp",
        "category": "messenger",
        "scraped_at": "2026-09-07T10:00:00+00:00",
        "score": 4.3,
        "ratings": 123456,
        "reviews": 7890,
        "min_installs": 1000000000,
        "version": "2.24.1",
        "store_last_updated": 1757251200,
        "ad_supported": False,
    }
    payload.update(overrides)
    return payload


def make_review_payload(**overrides) -> dict:
    payload = {
        "app_id": 1,
        "package_name": "com.whatsapp",
        "review_id": "abc123",
        "at": "2026-09-07T12:30:00",
        "user_name": "Jane Doe",
        "thumbs_up_count": 12,
        "score": 5,
        "content": "Great app!",
    }
    payload.update(overrides)
    return payload


def test_parse_stats_message_shapes_and_renames_fields():
    stats = parse_stats_message(make_stats_payload())

    assert stats["app_id"] == 1
    assert stats["reviews_count"] == 7890
    assert stats["store_updated_at"] == datetime.fromtimestamp(1757251200, tz=UTC)
    assert stats["fetched_at"] == datetime.fromisoformat("2026-09-07T10:00:00+00:00")


def test_parse_stats_message_missing_app_id_raises():
    with pytest.raises(InvalidMessageError):
        parse_stats_message(make_stats_payload(app_id=None))


def test_parse_stats_message_missing_scraped_at_raises():
    payload = make_stats_payload()
    del payload["scraped_at"]
    with pytest.raises(InvalidMessageError):
        parse_stats_message(payload)


def test_parse_review_message_missing_review_id_raises():
    with pytest.raises(InvalidMessageError):
        parse_review_message(make_review_payload(review_id=None))


async def test_stats_message_produces_a_new_row(session_factory):
    async with session_factory() as session:
        await insert_stats_snapshot(session, parse_stats_message(make_stats_payload()))

    async with session_factory() as session:
        rows = (await session.execute(select(AppStatsSnapshot))).scalars().all()

    assert len(rows) == 1
    assert rows[0].app_id == 1
    assert rows[0].min_installs == 1000000000


async def test_two_stats_messages_for_same_app_produce_two_rows(session_factory):
    async with session_factory() as session:
        await insert_stats_snapshot(session, parse_stats_message(make_stats_payload(score=4.3)))
    async with session_factory() as session:
        await insert_stats_snapshot(session, parse_stats_message(make_stats_payload(score=4.5)))

    async with session_factory() as session:
        rows = (
            (await session.execute(select(AppStatsSnapshot).where(AppStatsSnapshot.app_id == 1)))
            .scalars()
            .all()
        )

    assert len(rows) == 2
    assert {row.score for row in rows} == {4.3, 4.5}


async def test_review_message_inserts_a_new_row(session_factory):
    async with session_factory() as session:
        await upsert_review(session, parse_review_message(make_review_payload()))

    async with session_factory() as session:
        row = await session.get(Review, "abc123")

    assert row is not None
    assert row.content == "Great app!"
    assert row.thumbs_up_count == 12
    assert row.first_seen_at == row.last_seen_at


async def test_reprocessing_same_review_id_updates_fields_but_keeps_first_seen_at(session_factory):
    async with session_factory() as session:
        await upsert_review(session, parse_review_message(make_review_payload()))
    async with session_factory() as session:
        original = await session.get(Review, "abc123")
        original_first_seen_at = original.first_seen_at
        original_last_seen_at = original.last_seen_at

    async with session_factory() as session:
        await upsert_review(
            session,
            parse_review_message(make_review_payload(thumbs_up_count=99, content="Updated content", score=1)),
        )

    async with session_factory() as session:
        updated = await session.get(Review, "abc123")

    assert updated.thumbs_up_count == 99
    assert updated.content == "Updated content"
    assert updated.score == 1
    assert updated.first_seen_at == original_first_seen_at
    assert updated.last_seen_at >= original_last_seen_at

    async with session_factory() as session:
        rows = (await session.execute(select(Review))).scalars().all()
    assert len(rows) == 1
