"""Wraps google-play-scraper (a synchronous, blocking library) to fetch
general Google Play Store app stats, and shapes the result into the payload
this service publishes onto the message broker.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from google_play_scraper import app as fetch_play_store_app


async def scrape_app_details(package_name: str, lang: str, country: str) -> dict[str, Any]:
    """Fetch an app's current Play Store listing details.

    Runs the blocking google-play-scraper call in a thread so it doesn't
    block the event loop other apps in the same scrape pass are waiting on.
    """
    return await asyncio.to_thread(fetch_play_store_app, package_name, lang=lang, country=country)


def build_stats_payload(tracked_app: dict[str, Any], play_details: dict[str, Any]) -> dict[str, Any]:
    """Combine an app-list-api row with scraped Play Store details into one message payload."""
    return {
        "app_id": tracked_app["id"],
        "package_name": tracked_app["package_name"],
        "category": tracked_app["category"],
        "scraped_at": datetime.now(UTC).isoformat(),
        "title": play_details.get("title"),
        "score": play_details.get("score"),
        "ratings": play_details.get("ratings"),
        "reviews": play_details.get("reviews"),
        "installs": play_details.get("installs"),
        "min_installs": play_details.get("minInstalls"),
        "real_installs": play_details.get("realInstalls"),
        "free": play_details.get("free"),
        "price": play_details.get("price"),
        "currency": play_details.get("currency"),
        "genre": play_details.get("genre"),
        "content_rating": play_details.get("contentRating"),
        "version": play_details.get("version"),
        "store_last_updated": play_details.get("updated"),
    }
