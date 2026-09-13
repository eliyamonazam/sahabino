import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from sentiment.classifier import Sentiment, classify_sentiment
from sentiment.config import Config, get_config
from sentiment.database import build_session_factory
from sentiment.persistence import fetch_unscored_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sentiment-analyzer")


async def _process_batch(
    session_factory: async_sessionmaker, batch_size: int
) -> tuple[int, dict[Sentiment, int]]:
    """Classify and persist one batch. Returns (rows processed, label counts)."""
    counts: dict[Sentiment, int] = {"positive": 0, "neutral": 0, "negative": 0}
    async with session_factory() as session:
        batch = await fetch_unscored_batch(session, batch_size)
        for review in batch:
            label = classify_sentiment(review.content)
            review.sentiment = label
            counts[label] += 1
        await session.commit()
    return len(batch), counts


async def run_once(session_factory: async_sessionmaker, batch_size: int) -> dict[Sentiment, int]:
    """Classify every `sentiment IS NULL` review, one batch at a time, and exit.

    Naturally idempotent: each batch only ever selects rows still missing a
    sentiment, so a run stopped partway through (or one racing new rows
    inserted concurrently by storage-consumer) just leaves fewer, or more,
    rows for the next run to pick up -- no separate resume/dedup state needed.
    """
    totals: dict[Sentiment, int] = {"positive": 0, "neutral": 0, "negative": 0}
    processed = 0
    while True:
        batch_count, counts = await _process_batch(session_factory, batch_size)
        if batch_count == 0:
            break
        processed += batch_count
        for label, count in counts.items():
            totals[label] += count
        logger.info(
            "Classified batch of %d review(s) (positive=%d neutral=%d negative=%d) - %d processed so far",
            batch_count,
            counts["positive"],
            counts["neutral"],
            counts["negative"],
            processed,
        )
    return totals


async def main() -> None:
    config: Config = get_config()
    session_factory = build_session_factory()

    logger.info("Starting sentiment analysis pass (batch_size=%d)", config.batch_size)
    totals = await run_once(session_factory, config.batch_size)
    total_processed = sum(totals.values())
    if total_processed == 0:
        logger.info("No reviews awaiting classification.")
    else:
        logger.info(
            "Done: %d review(s) classified (positive=%d neutral=%d negative=%d)",
            total_processed,
            totals["positive"],
            totals["neutral"],
            totals["negative"],
        )


if __name__ == "__main__":
    asyncio.run(main())
