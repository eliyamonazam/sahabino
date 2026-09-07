import asyncio
import logging

import httpx

from message_broker import get_broker
from scraper.app_list_client import AppListClient
from scraper.config import Config, get_config
from scraper.playstore import build_stats_payload, scrape_app_details
from scraper.reviews import build_review_payload, scrape_app_reviews

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("playstore-scraper")


async def _scrape_and_publish_stats(tracked_app: dict, broker, config: Config) -> None:
    """Scrape one app's Play Store stats and publish them; log and skip on failure."""
    package_name = tracked_app["package_name"]
    try:
        play_details = await scrape_app_details(package_name, config.playstore_lang, config.playstore_country)
    except Exception:
        logger.exception("Failed to scrape %s, skipping", package_name)
        return

    payload = build_stats_payload(tracked_app, play_details)
    await broker.publish(config.playstore_topic, payload)
    logger.info("Published stats for %s", package_name)


async def _scrape_and_publish_reviews(tracked_app: dict, broker, config: Config) -> None:
    """Scrape one app's recent reviews and publish each as its own message; log and skip on failure."""
    package_name = tracked_app["package_name"]
    try:
        raw_reviews = await scrape_app_reviews(package_name, config.playstore_lang, config.playstore_country)
    except Exception:
        logger.exception("Failed to scrape reviews for %s, skipping", package_name)
        return

    for raw_review in raw_reviews:
        review_payload = build_review_payload(tracked_app, raw_review)
        await broker.publish(config.playstore_reviews_topic, review_payload)
    logger.info("Published %d reviews for %s", len(raw_reviews), package_name)


async def run_once(app_list_client: AppListClient, broker, config: Config) -> None:
    tracked_apps = await app_list_client.fetch_active_apps()
    logger.info("Scraping %d active apps", len(tracked_apps))

    for tracked_app in tracked_apps:
        await _scrape_and_publish_stats(tracked_app, broker, config)
        await _scrape_and_publish_reviews(tracked_app, broker, config)


async def main() -> None:
    config = get_config()

    async with httpx.AsyncClient(base_url=config.app_list_api_url) as http_client:
        app_list_client = AppListClient(http_client)
        async with get_broker() as broker:
            while True:
                try:
                    await run_once(app_list_client, broker, config)
                except Exception:
                    logger.exception("Scrape pass failed, will retry next interval")
                logger.info("Sleeping %ds until next scrape pass", config.scrape_interval_seconds)
                await asyncio.sleep(config.scrape_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
