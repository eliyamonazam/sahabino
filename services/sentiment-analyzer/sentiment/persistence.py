"""Reads unscored reviews and writes classification results back to Postgres."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentiment.models.review import Review


async def fetch_unscored_batch(session: AsyncSession, limit: int) -> list[Review]:
    """Fetch up to `limit` reviews still awaiting classification.

    Ordered by review_id for deterministic, reproducible batches (useful for
    tests and for reasoning about progress in the logs) -- order has no
    effect on correctness, since every `sentiment IS NULL` row eventually
    gets processed regardless of the order batches come back in.
    """
    stmt = select(Review).where(Review.sentiment.is_(None)).order_by(Review.review_id).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
