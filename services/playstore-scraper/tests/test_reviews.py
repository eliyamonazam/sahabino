from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from scraper.reviews import MAX_REVIEWS, build_review_payload, scrape_app_reviews


class FakeContinuationToken:
    def __init__(self, token):
        self.token = token


def make_raw_reviews(n, start=0):
    return [
        {
            "reviewId": f"r{i}",
            "userName": f"user{i}",
            "content": f"review body {i}",
            "score": 4,
            "thumbsUpCount": i,
            "at": datetime(2026, 9, 7, 12, 0, 0),
        }
        for i in range(start, start + n)
    ]


async def test_scrape_app_reviews_stops_at_max_when_more_pages_available():
    # Each page returns REVIEWS_PAGE_SIZE (200) reviews with a non-None
    # continuation token, so the library reports more pages are always
    # available. Collection should still stop once MAX_REVIEWS is reached.
    pages = [(make_raw_reviews(200, start=i * 200), FakeContinuationToken("next")) for i in range(10)]

    with patch("scraper.reviews.fetch_reviews_page", side_effect=pages) as mock_fetch:
        result = await scrape_app_reviews("com.whatsapp", lang="fa", country="ir")

    assert len(result) == MAX_REVIEWS
    assert mock_fetch.call_count == MAX_REVIEWS // 200


async def test_scrape_app_reviews_stops_early_when_pages_run_out():
    pages = [
        (make_raw_reviews(200, start=0), FakeContinuationToken("next")),
        (make_raw_reviews(50, start=200), FakeContinuationToken(None)),
    ]

    with patch("scraper.reviews.fetch_reviews_page", side_effect=pages) as mock_fetch:
        result = await scrape_app_reviews("com.whatsapp", lang="fa", country="ir")

    assert len(result) == 250
    assert mock_fetch.call_count == 2


def test_build_review_payload_shapes_and_renames_fields():
    raw_review = {
        "reviewId": "abc123",
        "userName": "Jane Doe",
        "content": "Great app!",
        "score": 5,
        "thumbsUpCount": 12,
        "at": datetime(2026, 9, 7, 12, 30, 0),
    }
    tracked_app = {"id": 1, "package_name": "com.whatsapp"}

    payload = build_review_payload(tracked_app, raw_review)

    assert payload == {
        "app_id": 1,
        "package_name": "com.whatsapp",
        "review_id": "abc123",
        "at": "2026-09-07T12:30:00",
        "user_name": "Jane Doe",
        "thumbs_up_count": 12,
        "score": 5,
        "content": "Great app!",
    }


def test_build_review_payload_tolerates_missing_fields():
    payload = build_review_payload({"id": 1, "package_name": "com.whatsapp"}, {})

    assert payload["review_id"] is None
    assert payload["at"] is None
    assert payload["user_name"] is None


async def test_scrape_app_reviews_retries_with_backoff_then_gives_up():
    with (
        patch("scraper.reviews.fetch_reviews_page", side_effect=RuntimeError("boom")) as mock_fetch,
        patch("scraper.reviews.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        pytest.raises(RuntimeError, match="boom"),
    ):
        await scrape_app_reviews("com.whatsapp", lang="fa", country="ir")

    assert mock_fetch.call_count == 4
    assert mock_sleep.call_count == 3
    mock_sleep.assert_any_call(2)
    mock_sleep.assert_any_call(4)
    mock_sleep.assert_any_call(8)


async def test_scrape_app_reviews_recovers_after_transient_failures():
    side_effect = [
        RuntimeError("rate limited"),
        RuntimeError("rate limited"),
        (make_raw_reviews(10), FakeContinuationToken(None)),
    ]

    with (
        patch("scraper.reviews.fetch_reviews_page", side_effect=side_effect),
        patch("scraper.reviews.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        result = await scrape_app_reviews("com.whatsapp", lang="fa", country="ir")

    assert len(result) == 10
    assert mock_sleep.call_count == 2
