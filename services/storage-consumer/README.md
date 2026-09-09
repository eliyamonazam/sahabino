# storage-consumer

Consumes both topics `playstore-scraper` publishes to (`playstore-app-stats`
and `playstore-app-reviews`) via `libs/message_broker`'s `get_broker()`, and
persists them into Postgres. Backend selection (Redis Streams vs Kafka)
follows the same `MESSAGE_BROKER_TYPE` environment variable convention as
the scraper, so this service works against either without code changes —
Kafka is the broker actually used in the deployed stack.

Runs two concurrent consume loops (`asyncio.gather`, one per topic), each
under its own consumer group (`storage-consumer-stats` /
`storage-consumer-reviews`) so it can scale to multiple replicas later
without double-processing a message.

## Schema

This service owns two tables via its own Alembic history
(`alembic/versions/`), independent of app-list-api-fastapi's:

- **`app_stats_snapshots`** — one row per stats message, append-only.
  History is intentionally never updated in place, so later analysis
  (trend charts, etc.) can see every scrape, not just the latest one.
- **`reviews`** — one row per unique review, upserted on `review_id`.
  `first_seen_at` is set once, on first insert; `last_seen_at` is bumped on
  every write. `sentiment` is left unused (nullable) for now, and the
  upsert is written so a re-scrape never overwrites it with NULL, leaving
  room for a future sentiment-analysis job to populate it independently.

`app_id` on both tables is a **plain indexed integer, not a foreign key**.
The `apps` table it logically references is owned by
`app-list-api-fastapi`'s own Alembic migrations; adding a cross-service FK
here would couple this service's schema history to that other service's,
even though the two are meant to evolve independently. The reference is
enforced at the application level (the scraper only ever emits `app_id`
values that came from `app-list-api-fastapi` in the first place), not at
the database level.

## Message handling

- **Stats messages**: always insert a new `app_stats_snapshots` row.
  `fetched_at` comes from the message's own `scraped_at` field, not from
  when this service happens to process it.
- **Review messages**: `INSERT ... ON CONFLICT (review_id) DO UPDATE`,
  updating every scraped field except `first_seen_at`.
- A message is only `ack()`'d after it has been successfully committed to
  Postgres. If processing a single message fails (missing required fields,
  a DB error), it's logged and skipped, left unacked so the broker
  redelivers it, and the loop moves on to the next message rather than
  crashing.

Note: this service shares its Postgres database (not just the instance) with
`app-list-api-fastapi`, which also uses Alembic. Alembic's default
`alembic_version` bookkeeping table would collide between the two services'
independent histories, so this service's `alembic/env.py` configures a
distinct `version_table` (`alembic_version_storage_consumer`).

## Running migrations

```bash
docker compose run --rm storage-consumer alembic upgrade head
```

(Also runs automatically on container start, before `python -m consumer.main`.)

## Tests

Same pattern as the other services: a real Postgres test database
(`POSTGRES_TEST_DB_STORAGE_CONSUMER`, separate from every other service's
test database), no mocking of Postgres itself.

```bash
docker compose run --rm -e POSTGRES_HOST=postgres storage-consumer \
  sh -c "pip install -r requirements-dev.txt && pytest"
```
