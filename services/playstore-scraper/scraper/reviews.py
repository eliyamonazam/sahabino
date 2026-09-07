"""Wraps google-play-scraper's paginated reviews endpoint (a synchronous,
blocking library) to fetch an app's most recent reviews, and shapes each one
into the payload this service publishes onto the message broker.
"""

import asyncio
import logging
from typing import Any

from google_play_scraper import Sort
from google_play_scraper import reviews as fetch_reviews_page

logger = logging.getLogger("playstore-scraper")

MAX_REVIEWS = 1000
REVIEWS_PAGE_SIZE = 200
RETRY_ATTEMPTS = 4
INITIAL_BACKOFF_SECONDS = 2
MAX_BACKOFF_SECONDS = 60


async def _fetch_page_with_retry(
    package_name: str, lang: str, country: str, count: int, continuation_token: Any
) -> tuple[list[dict[str, Any]], Any]:
    """Fetch one page of reviews, retrying transient failures with exponential backoff."""
    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return await asyncio.to_thread(
                fetch_reviews_page,
                package_name,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=count,
                continuation_token=continuation_token,
            )
        except Exception:
            if attempt == RETRY_ATTEMPTS:
                raise
            logger.warning(
                "Review page fetch for %s failed (attempt %d/%d), retrying in %ds",
                package_name,
                attempt,
                RETRY_ATTEMPTS,
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)


async def scrape_app_reviews(package_name: str, lang: str, country: str) -> list[dict[str, Any]]:
    """Fetch up to MAX_REVIEWS most recent reviews for an app.

    Pages through google-play-scraper's reviews() via its continuation token
    until MAX_REVIEWS reviews have been collected or the library reports
    there are no more pages, whichever comes first.
    """
    collected: list[dict[str, Any]] = []
    continuation_token = None

    while len(collected) < MAX_REVIEWS:
        page, continuation_token = await _fetch_page_with_retry(
            package_name,
            lang,
            country,
            min(REVIEWS_PAGE_SIZE, MAX_REVIEWS - len(collected)),
            continuation_token,
        )
        collected.extend(page)

        if continuation_token is None or continuation_token.token is None:
            break

    return collected[:MAX_REVIEWS]


def build_review_payload(tracked_app: dict[str, Any], raw_review: dict[str, Any]) -> dict[str, Any]:
    """Combine an app-list-api row with one scraped review into a publish payload."""
    at = raw_review.get("at")
    return {
        "app_id": tracked_app["id"],
        "package_name": tracked_app["package_name"],
        "review_id": raw_review.get("reviewId"),
        "at": at.isoformat() if at is not None else None,
        "user_name": raw_review.get("userName"),
        "thumbs_up_count": raw_review.get("thumbsUpCount"),
        "score": raw_review.get("score"),
        "content": raw_review.get("content"),
    }
