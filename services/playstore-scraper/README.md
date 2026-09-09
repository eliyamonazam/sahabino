# playstore-scraper

Collects Google Play Store app metadata and publishes it to the message
broker for downstream storage.

This covers general app stats (title, rating, install count, etc.) and each
app's latest reviews, both via
[google-play-scraper](https://pypi.org/project/google-play-scraper/) — not
the network-traffic-driven work.

## How it works

1. Fetches the current list of active tracked apps from `app-list-api-fastapi`
   (`GET /apps?active_only=true`) — that service stays the single source of
   truth for which apps exist and their categories.
2. For each app:
   - Scrapes its Play Store listing and shapes the result into a flat payload
     (`scraper/playstore.py:build_stats_payload`), published as one message on
     the `playstore-app-stats` topic.
   - Scrapes up to its 1000 most recent reviews, newest first
     (`scraper/reviews.py:scrape_app_reviews`), and publishes each one as its
     own message (`build_review_payload`) on the `playstore-app-reviews`
     topic. A page fetch that fails transiently (e.g. rate-limited) is
     retried with exponential backoff before giving up on that app's reviews
     for this pass.
3. Both topics are published via `libs/message_broker` (backend selected by
   `MESSAGE_BROKER_TYPE`).
4. Sleeps `SCRAPE_INTERVAL_SECONDS` (default 3600) and repeats.

A failure scraping one app's stats or reviews (e.g. the listing was pulled,
transient network error, retries exhausted) is logged and skipped — it
doesn't stop the rest of that pass, and a stats failure doesn't prevent that
same app's reviews from being attempted (or vice versa).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `APP_LIST_API_URL` | `http://app-list-api-fastapi:8000` | Base URL of the app-list-api-fastapi service |
| `MESSAGE_BROKER_TYPE` | `kafka` | `redis` or `kafka`, see `libs/message_broker`. Kafka is the broker used in the deployed stack. |
| `SCRAPE_INTERVAL_SECONDS` | `3600` | Delay between scrape passes |
| `PLAYSTORE_LANG` | `fa` | Locale passed to google-play-scraper |
| `PLAYSTORE_COUNTRY` | `ir` | Storefront country passed to google-play-scraper |
| `PLAYSTORE_TOPIC` | `playstore-app-stats` | Topic app stats are published to |
| `PLAYSTORE_REVIEWS_TOPIC` | `playstore-app-reviews` | Topic reviews are published to |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests mock the two external boundaries (the Play Store scrape call and the
app-list-api HTTP call) — no live network or running services required.
