"""Writes already-parsed stats/review dicts (see parsing.py) to Postgres."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from consumer.models.review import Review
from consumer.models.stats import AppStatsSnapshot


async def insert_stats_snapshot(session: AsyncSession, stats: dict[str, Any]) -> None:
    """Insert one append-only row. Never updates an existing row."""
    session.add(AppStatsSnapshot(**stats))
    await session.commit()


async def upsert_review(session: AsyncSession, review: dict[str, Any]) -> None:
    """Insert a new review, or update an existing one's scraped fields.

    `first_seen_at` is set only on insert. `last_seen_at` is set to now on
    every write. `sentiment` is excluded from the update entirely so a
    re-scrape never overwrites a value written by a separate analysis job.
    """
    now = datetime.now(UTC)
    stmt = pg_insert(Review).values(**review, first_seen_at=now, last_seen_at=now)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Review.review_id],
        set_={
            "app_id": stmt.excluded.app_id,
            "at": stmt.excluded.at,
            "user_name": stmt.excluded.user_name,
            "thumbs_up_count": stmt.excluded.thumbs_up_count,
            "score": stmt.excluded.score,
            "content": stmt.excluded.content,
            "last_seen_at": stmt.excluded.last_seen_at,
        },
    )
    await session.execute(stmt)
    await session.commit()
