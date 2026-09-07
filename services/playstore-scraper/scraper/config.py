"""Scraper configuration, read from environment variables.

Reuses conventions from the app-list-api services: load the repo-root .env
as a convenience for running outside docker compose, where it's already a
no-op since environment variables are injected directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_parents = Path(__file__).resolve().parents
if len(_parents) > 3 and (_parents[3] / ".env").exists():
    load_dotenv(_parents[3] / ".env")


class Config:
    def __init__(self) -> None:
        self.app_list_api_url = os.getenv("APP_LIST_API_URL", "http://app-list-api-fastapi:8000")
        self.playstore_topic = os.getenv("PLAYSTORE_TOPIC", "playstore-app-stats")
        self.scrape_interval_seconds = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "3600"))
        self.playstore_lang = os.getenv("PLAYSTORE_LANG", "fa")
        self.playstore_country = os.getenv("PLAYSTORE_COUNTRY", "ir")


def get_config() -> Config:
    return Config()
