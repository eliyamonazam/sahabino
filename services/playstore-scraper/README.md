# playstore-scraper

Collects Google Play Store app metadata and publishes it to the message
broker for downstream storage.

This first pass covers general app stats only (title, rating, install count,
etc. — via [google-play-scraper](https://pypi.org/project/google-play-scraper/)),
not the network-traffic-driven work.

## How it works

1. Fetches the current list of active tracked apps from `app-list-api-fastapi`
   (`GET /apps?active_only=true`) — that service stays the single source of
   truth for which apps exist and their categories.
2. For each app, scrapes its Play Store listing and shapes the result into a
   flat payload (`scraper/playstore.py:build_stats_payload`).
3. Publishes one message per app onto the `playstore-app-stats` topic via
   `libs/message_broker` (backend selected by `MESSAGE_BROKER_TYPE`).
4. Sleeps `SCRAPE_INTERVAL_SECONDS` (default 3600) and repeats.

A failure scraping one app (e.g. the listing was pulled, transient network
error) is logged and skipped — it doesn't stop the rest of that pass.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `APP_LIST_API_URL` | `http://app-list-api-fastapi:8000` | Base URL of the app-list-api-fastapi service |
| `MESSAGE_BROKER_TYPE` | `redis` | `redis` or `kafka`, see `libs/message_broker` |
| `SCRAPE_INTERVAL_SECONDS` | `3600` | Delay between scrape passes |
| `PLAYSTORE_LANG` | `fa` | Locale passed to google-play-scraper |
| `PLAYSTORE_COUNTRY` | `ir` | Storefront country passed to google-play-scraper |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests mock the two external boundaries (the Play Store scrape call and the
app-list-api HTTP call) — no live network or running services required.
