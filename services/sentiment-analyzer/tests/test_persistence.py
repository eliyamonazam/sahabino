from datetime import UTC, datetime

from sentiment.classifier import classify_sentiment
from sentiment.main import run_once
from sentiment.models.review import Review
from sentiment.persistence import fetch_unscored_batch
from sqlalchemy import select, text


async def _insert_review(
    session_factory, review_id: str, content: str | None, sentiment: str | None = None
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO reviews
                    (review_id, app_id, content, sentiment, first_seen_at, last_seen_at)
                VALUES
                    (:review_id, 1, :content, :sentiment, :now, :now)
                """
            ),
            {"review_id": review_id, "content": content, "sentiment": sentiment, "now": now},
        )
        await session.commit()


async def test_fetch_unscored_batch_only_returns_null_sentiment_rows(session_factory):
    await _insert_review(session_factory, "already-scored", "عالی", sentiment="positive")
    await _insert_review(session_factory, "unscored", "افتضاح بود")

    async with session_factory() as session:
        batch = await fetch_unscored_batch(session, limit=10)

    assert [review.review_id for review in batch] == ["unscored"]


async def test_fetch_unscored_batch_respects_limit(session_factory):
    for i in range(5):
        await _insert_review(session_factory, f"review-{i}", "خوب")

    async with session_factory() as session:
        batch = await fetch_unscored_batch(session, limit=3)

    assert len(batch) == 3


async def test_run_once_classifies_every_unscored_review_and_is_idempotent(session_factory):
    await _insert_review(session_factory, "pos-1", "عالی")
    await _insert_review(session_factory, "neg-1", "افتضاح")
    await _insert_review(session_factory, "neu-1", "سید احمد")

    totals = await run_once(session_factory, batch_size=2)
    assert totals == {"positive": 1, "neutral": 1, "negative": 1}

    async with session_factory() as session:
        result = await session.execute(select(Review).order_by(Review.review_id))
        rows = {review.review_id: review.sentiment for review in result.scalars().all()}
    assert rows == {"pos-1": "positive", "neg-1": "negative", "neu-1": "neutral"}

    # Idempotent: every row already has a sentiment, so a second pass finds
    # nothing left to do and touches nothing.
    second_pass_totals = await run_once(session_factory, batch_size=2)
    assert second_pass_totals == {"positive": 0, "neutral": 0, "negative": 0}


async def test_run_once_never_overwrites_an_existing_sentiment(session_factory):
    await _insert_review(session_factory, "manually-set", "افتضاح", sentiment="positive")

    await run_once(session_factory, batch_size=10)

    async with session_factory() as session:
        review = await session.get(Review, "manually-set")
    # Content says "afraid/terrible" (would classify negative), but the
    # existing value is left untouched since it wasn't NULL to begin with.
    assert review.sentiment == "positive"
    assert classify_sentiment(review.content) == "negative"
