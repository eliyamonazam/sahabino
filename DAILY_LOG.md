# Daily Log

## Day 1 — 2026-09-05

### Done
- Set up the repository skeleton with reserved `services/` folders for two parallel CRUD API implementations (FastAPI and Django) and separate services for the scraper, network analyzer, and storage consumer.
- Reserved a `libs/message_broker` folder for a broker abstraction that will support both Redis and Kafka.
- Wrote a `docker-compose.yml` with four infrastructure services: postgres, redis, kafka (KRaft mode, no zookeeper), and metabase, plus a matching `.env.example`.
- Wrote `scripts/setup.sh`, `scripts/run.sh`, and `scripts/stop.sh` to check prerequisites, start, and stop the stack.
- Added a git hook to keep commit messages free of tool-generated attribution lines.
- Wrote a `.gitignore` for a Python + Docker project, including local agent config files.
- Started the full stack with `docker compose up -d` and confirmed all four services reach a healthy/running state.

### Learned
<!-- TODO: do NOT fill this in. The user must fill this in themselves, in their own words, after reviewing what was actually built. -->

### Blockers / questions to raise
- Kafka in KRaft mode took roughly 10-20 seconds to report healthy on first boot; this is expected and the healthcheck has a 30s start period to account for it.
<!-- The user will add their own conceptual questions here -->

### Plan for tomorrow
- TODO

## Day 2 — 2026-09-05

### Done
- Built `services/app-list-api-fastapi`: a FastAPI CRUD service for the tracked-apps list, with an `App` SQLAlchemy model (`id`, `package_name` unique, `name`, `category` as a plain string with allowed values documented in a column comment, `is_active`, `created_at`, `updated_at`).
- Set up Alembic in this service with an async-engine `env.py` that reads the connection string from environment variables (never hardcoded), and generated the initial migration creating the `apps` table. This service's Alembic history is the schema source of truth for the table.
- Implemented `POST /apps`, `GET /apps` (with `active_only` filter), `PATCH /apps/{id}` (partial update of `package_name`, `name`, and/or `category`), and `DELETE /apps/{id}` (soft delete — sets `is_active = false`, never removes the row), all using Pydantic request/response models with field descriptions, so `/docs` renders useful Swagger UI docs. Duplicate `package_name` returns a clean 409 (on both create and update) instead of a leaked DB constraint error; unknown ids on PATCH/DELETE return 404.
- Wired the DB connection through an async SQLAlchemy engine (`asyncpg`) and a `get_db` FastAPI dependency, built from the same `POSTGRES_*` variables as the rest of the stack (plus `POSTGRES_HOST` and `POSTGRES_TEST_DB`, newly added to `.env.example`).
- Wrote a pytest suite (11 tests) covering all four endpoints plus edge cases (duplicate package_name on create and on update, invalid category, updating/deleting a non-existent id, active_only filtering), running against a separate `sahabino_test` database with fixtures that create the tables before the session and drop them after.
- Wrote a `Dockerfile` for the service and added `app-list-api-fastapi` to `docker-compose.yml`, exposed on port 8001, with `depends_on: postgres: condition: service_healthy`. Also upgraded `metabase`'s `depends_on` to the same explicit healthy-condition form (it previously only waited for postgres to start, not to be ready — a gap flagged on Day 1).
- Wrote `scripts/seed_apps.sh` and used it to seed the 16 initial apps across all six categories via the running API.
- Ran the full stack, re-ran the seed script, and verified end-to-end with curl: listing returns all 16 seeded apps, creating a duplicate `package_name` returns 409, patching an app's category persists and bumps `updated_at`, and deleting an app sets `is_active = false` while it still appears in the unfiltered list (and disappears with `active_only=true`).
- Same-day correction: moved the host-side Postgres port from `5432` to `5433` in `.env`/`.env.example` (the container-internal port stays `5432`) after finding a native Postgres service on this machine already bound to `5432`, which was silently intercepting host-side connections. Restarted the stack and confirmed postgres is healthy and reachable from the host on `localhost:5433`.
- Same-day correction: the user confirmed the real Google Play package ids for two apps — Baham (`ir.android.baham`) and Pinno (`app.pinno`). Corrected both rows via the now-extended `PATCH /apps/{id}` (which can now also update `package_name`, with the same 409-on-duplicate handling as create) and updated `scripts/seed_apps.sh` so a future fresh seed inserts the correct values directly.

### Learned
<!-- TODO: do NOT fill this in. The user must fill this in themselves, in their own words, after reviewing what was actually built. -->

### Blockers / questions to raise
- This machine has a native Windows PostgreSQL service also bound to host port 5432 (alongside Docker Desktop's port mapping for the `postgres` container), so tools run directly on the host (a local venv's `alembic`/`pytest`) can silently hit the wrong server on `localhost:5432` and fail auth. Worked around it by running migrations and tests inside a container attached to the compose network (via `docker compose run`) instead of from the host. Worth deciding whether to stop/reconfigure the native service or remap `POSTGRES_PORT` if host-side tooling needs to work directly against `localhost` going forward.
- The venv for this service must be created with Python 3.13, not the 3.14 interpreter that's first on this machine's PATH — `pydantic-core`'s pinned version has no prebuilt wheel for 3.14 yet (PyO3 doesn't support it), so pip falls back to a from-source build that hangs without a Rust toolchain installed.
- 9 of the 16 seeded apps still use placeholder package names (`com.placeholder.*`) rather than real Google Play ids — Baham and Pinno were corrected today (see above); the remaining 9 (all operator/video/word_game apps) still need to be looked up and corrected before Day 4's scraping work starts.
<!-- The user will add their own conceptual questions here -->

### Plan for tomorrow
- Implement the Django version of the same CRUD API (`services/app-list-api-django`) against the same `apps` table and the same Postgres database, using Django's ORM against the schema Alembic already created (Django migrations for this service should be faked/no-op against the existing table rather than re-creating it, since the FastAPI service's Alembic history stays the source of truth for the schema).
- Reuse the same four endpoints and behavior (soft-delete, active_only filter, 409 on duplicate package_name, 404 on missing id) so both implementations are interchangeable from a client's perspective.
- Add the Django service to `docker-compose.yml` on its own port, with the same `depends_on: postgres: condition: service_healthy` pattern.
- Write an equivalent pytest/Django test suite against a separate test database, mirroring today's FastAPI test coverage.

## Day 3 — 2026-09-05

### Done
- Built `services/app-list-api-django`: a second, independent CRUD implementation for the same `apps` table, using Django + Django REST Framework + drf-spectacular. Scaffolded via `django-admin startproject config .` and `python manage.py startapp apps_api`, with `INSTALLED_APPS`/`MIDDLEWARE` trimmed to what a pure JSON API service actually needs (no admin site, sessions, or auth app).
- Defined the `App` model (`apps_api/models.py`) with `Meta.managed = False` and `db_table = "apps"`, and an explicit `id = models.AutoField(...)` (not the project's default `BigAutoField`) so it matches the real column's 32-bit `integer` type exactly. Ran `makemigrations` to record the model state; confirmed `migrate` correctly no-ops the `apps` table (only creates Django's own `django_migrations`/`django_content_type` bookkeeping tables) and leaves the existing 16-row table completely untouched.
- Implemented `POST /apps/`, `GET /apps/` (`active_only` param), `PATCH /apps/{id}/` (partial update of `package_name`/`name`/`category`), and `DELETE /apps/{id}/` (soft delete) via a custom DRF `GenericViewSet`, restricted to exactly those four operations (no retrieve, no PUT). Duplicate `package_name` returns a clean 409 (via an `IntegrityError` catch, matching the FastAPI service's exact status code and message) on both create and update; unknown ids return DRF's standard 404.
- Wired `DATABASES` to the same `POSTGRES_*` environment variables as the FastAPI service, so both point at the identical `sahabino` database and `apps` table.
- Set up a `conftest.py` that overrides pytest-django's `django_db_setup` fixture to run the same `CREATE TABLE apps (...)` DDL as the FastAPI service's Alembic migration (copied by hand, with a comment flagging it needs to stay in sync) against a distinct test database (`sahabino_test_django`, separate from the FastAPI service's `sahabino_test`) before the test session, and drops it after.
- Wrote a DRF `APIClient` test suite (11 tests) mirroring the FastAPI service's coverage: create, duplicate package_name (create and patch), invalid category, list, active_only filtering, partial update including package_name, 404s on unknown id, and soft-delete behavior. All pass, both from a local venv and from inside the docker compose network.
- Wrote a `Dockerfile` (gunicorn, running `migrate --noinput` first) and added `app-list-api-django` to `docker-compose.yml` on port 8002, depending only on `postgres: condition: service_healthy` — deliberately not depending on `app-list-api-fastapi`, since the two are independent services that happen to share a database.
- Ran the manual cross-service consistency check: created an app via FastAPI's `POST /apps` and confirmed it appeared via Django's `GET /apps/`, then created one via Django's `POST /apps/` and confirmed it appeared via FastAPI's `GET /apps`. Both directions worked immediately (both test rows removed afterward) — confirms the two services are genuinely reading and writing the same table.

### Learned
<!-- TODO: do NOT fill this in. The user must fill this in themselves, in their own words, after reviewing what was actually built. -->

### Blockers / questions to raise
- DRF's default `UNAUTHENTICATED_USER` setting (`AnonymousUser`) lazily imports `django.contrib.auth.models` on every request, which fails once `django.contrib.auth` is removed from `INSTALLED_APPS` (as it is here, since this is an unauthenticated internal service with no sessions/admin). Fixed by explicitly setting `REST_FRAMEWORK["UNAUTHENTICATED_USER"] = None`; worth remembering if a future trimmed-down Django service hits the same failure.
- Declaring `package_name` explicitly on the DRF serializer (rather than letting `ModelSerializer` auto-generate it from the model field) means DRF's automatic `UniqueValidator` is not attached — duplicate detection relies entirely on the DB-level `IntegrityError` catch instead. This was actually the desired outcome here (a clean 409 matching FastAPI exactly, rather than DRF's usual 400), but it's a subtle DRF behavior worth being aware of if the serializer is refactored later.
- Still unresolved from Day 2: 9 of the 16 seeded apps use placeholder package names (`com.placeholder.*`) and need real Google Play ids looked up before Day 4's scraping work starts.
<!-- The user will add their own conceptual questions here -->

### Plan for tomorrow
- Build a shared `MessageBroker` abstraction in `libs/message_broker/` — a common interface (e.g. `publish`/`subscribe` or `produce`/`consume`) with two concrete implementations, one backed by Redis Streams and one backed by Kafka, so downstream services (the scraper, storage consumer, network analyzer) can be written against the abstraction and swap brokers via configuration.
- Start the Playstore scraper service (`services/playstore-scraper`), first half: general app stats only (name, rating, install count, etc. — not yet the network-traffic-driven work) for the apps currently in the `apps` table, published onto the broker abstraction built the same day.
- Before scraping begins in earnest, resolve the remaining 9 placeholder package names flagged since Day 2, since the scraper needs real Google Play ids to look up.

## Day 4 — 2026-09-07

### Done
- Resolved all 9 remaining placeholder package names (operator, video, and word_game apps) to real Google Play ids and updated `scripts/seed_apps.sh` so a fresh seed inserts them directly, the same pattern used for Baham/Pinno on Day 2: Myirancell → `com.myirancell`, Mymci → `ir.mci.ecareapp`, MyRightel → `ir.rightel.myrightel`, Namava → `com.shatelland.namava.mobile`, Lenz → `com.likotv`, Tamashakhonehtv → `ir.tamashakhonehtv`, Fandogh → `com.plus9.fandogh`, Amirza → `com.BrainLadder.AmirzaGP`, Samavar → `com.plus9.samavar`.
- Built `libs/message_broker`: a `MessageBroker` ABC (`publish`/`consume`/`ack`, both backends using named consumer groups and explicit at-least-once acking) with two implementations — `RedisStreamsBroker` (XADD/XREADGROUP/XACK via `redis.asyncio`) and `KafkaBroker` (aiokafka, manual offset commits so `ack()` has the same semantics on both backends). Backend selection is via `MESSAGE_BROKER_TYPE` (`redis`/`kafka`, default `redis`), added to `.env.example`. Packaged as an installable library (`pyproject.toml`, importable as `message_broker`) so services depend on it as an editable path requirement.
- Wrote integration tests for both broker implementations (no mocks, matching this repo's existing convention) — publish→consume→ack round trip and message-ordering, run against the real `redis`/`kafka` containers. All 5 pass.
- Built `services/playstore-scraper`: fetches the active app list from `app-list-api-fastapi` (`GET /apps?active_only=true` — that service stays the source of truth for which apps to track), scrapes each app's Play Store listing via `google-play-scraper` (run off the event loop with `asyncio.to_thread` since it's a blocking library), shapes the result into a flat stats payload, and publishes one message per app onto the `playstore-app-stats` topic via the broker abstraction. Loops on `SCRAPE_INTERVAL_SECONDS` (default 3600); a single app's scrape failure is logged and skipped without stopping the rest of the pass.
- Wrote a unit test suite (5 tests, mocking only the two external boundaries — the Play Store call and the app-list-api HTTP call) covering payload shaping, missing-field tolerance, and the app-list-api client. All pass.
- Added `playstore-scraper` to `docker-compose.yml` (build context is the repo root so its Dockerfile can `COPY` in `libs/message_broker`), depending on `app-list-api-fastapi` (started) and `redis`/`kafka` (healthy).
- Brought up the full stack fresh (`docker compose up -d --build`), re-ran `scripts/seed_apps.sh` with the corrected package names (all 16 apps created cleanly against both API services), and verified the scraper end-to-end: 15 of 16 active apps scraped and published successfully on the first real pass, confirmed by reading the messages back directly from the `playstore-app-stats` Redis stream (`XLEN`/`XRANGE`) — full realistic payloads (title, score, ratings, installs, genre, etc., in Persian where the store returns it) landed correctly.

### Learned
<!-- TODO: do NOT fill this in. The user must fill this in themselves, in their own words, after reviewing what was actually built. -->

### Blockers / questions to raise
- `ir.rightel.myrightel` (MyRightel) 404s on every scrape attempt — verified directly against the Play Store listing (not a scraper bug or a wrong package id): the app was reportedly removed from Google Play in mid-2024 and is no longer listed there at all. The scraper's per-app skip-and-log handling means this doesn't block the rest of the pass, but the app currently has no Play Store stats to collect; worth deciding whether to mark it inactive, find an alternative source, or just accept the gap.
- `app-list-api-fastapi` has no Docker healthcheck (only `postgres`/`redis`/`kafka` do), so `playstore-scraper`'s `depends_on` can only wait for it to *start*, not to actually be ready — on a fresh `docker compose up`, the scraper's very first scheduled pass raced uvicorn's startup and failed with a connection error before the 1-hour retry interval. Recovering just required restarting the scraper container once the API was actually up; consider adding a healthcheck to `app-list-api-fastapi` (and `-django`) if this keeps being noisy on cold starts.
- `libs/message_broker`'s tests and the scraper's own tests both need a real Python venv per package (each has its own `requirements-dev.txt`); there's no repo-wide "run everything" test command yet now that there are four independently-testable Python components.
<!-- The user will add their own conceptual questions here -->

### Plan for tomorrow
- Build `services/storage-consumer`: consume from the `playstore-app-stats` topic via the broker abstraction and persist scraped stats into a new table (schema TBD — likely one row per scrape per app, not an update-in-place, so history is preserved for later analysis).
- Decide how to handle `ir.rightel.myrightel` being delisted (mark inactive vs. accept the gap) before it causes confusing "missing data" questions downstream.
- Consider adding Docker healthchecks to `app-list-api-fastapi`/`app-list-api-django` so dependent services' `depends_on: condition: service_healthy` can be trusted the way it already is for `postgres`/`redis`/`kafka`.

## Day 6 — 2026-09-07

### Done
- Built `services/storage-consumer`, with its own async Alembic setup (same pattern as `app-list-api-fastapi`'s) owning two new tables: `app_stats_snapshots` (append-only, one row inserted per stats message, never updated) and `reviews` (one row per unique `review_id`, upserted via `INSERT ... ON CONFLICT DO UPDATE`). `app_id` on both tables is a plain indexed integer, not a foreign key, since the `apps` table it logically references belongs to `app-list-api-fastapi`'s own migration history; this is documented in the new service's README.
- Discovered and fixed a real migration-tooling collision: this service shares the same `sahabino` Postgres database with `app-list-api-fastapi`, and both use Alembic, so Alembic's default `alembic_version` bookkeeping table would collide between the two independent migration histories. Fixed by giving this service's `alembic/env.py` a distinct `version_table` (`alembic_version_storage_consumer`).
- Implemented the consumer: `consumer/parsing.py` validates and shapes a raw broker payload (raising on a missing required field), `consumer/persistence.py` writes the parsed dict to Postgres, and `consumer/main.py` runs two concurrent loops via `asyncio.gather` (one per topic, each under its own consumer group — `storage-consumer-stats` / `storage-consumer-reviews`), reusing `libs/message_broker`'s `get_broker()` so the service works against Redis or Kafka via `MESSAGE_BROKER_TYPE` with no code changes. A message is only `ack()`'d after a successful commit; one that fails to parse or write is logged and left unacked so the broker redelivers it, and the loop moves on to the next message rather than crashing.
- Wrote 10 pytest tests against a real, separate test database (`sahabino_test_storage_consumer`, via a new `POSTGRES_TEST_DB_STORAGE_CONSUMER` variable added to `.env`/`.env.example`): a stats message produces a new row and two stats messages for the same app produce two rows (append-only); reprocessing the same `review_id` updates every scraped field and bumps `last_seen_at` while `first_seen_at` stays exactly as it was on first insert; a malformed message (missing required fields) is logged and skipped without crashing the loop or blocking the valid messages before/after it in the same batch. All pass.
- Added `storage-consumer` to `docker-compose.yml`, depending on `postgres`/`redis`/`kafka` with `condition: service_healthy` (not on `app-list-api-fastapi`, since this service never calls that API directly).
- Ran the first genuine end-to-end pass of the whole pipeline. With `MESSAGE_BROKER_TYPE=redis`, one scrape pass landed 7 `app_stats_snapshots` rows and 6100 `reviews` rows in Postgres for the 7 currently-real (non-placeholder) apps, confirmed by querying Postgres directly rather than trusting the logs. Switching to `MESSAGE_BROKER_TYPE=kafka` and restarting the scraper and storage-consumer containers, a second pass landed 6 more stats rows (13 total) and 16 more/updated review rows (6116 total) through the Kafka path — including one review whose `first_seen_at` (set during the Redis pass) was confirmed unchanged while its `last_seen_at` was bumped by the later Kafka pass, proving the dedup/upsert logic behaves identically across both broker backends.
- Found and fixed a genuine Kafka misconfiguration, surfaced because this was the first time two actual services (not host-side test code) exchanged Kafka traffic over the compose network: `docker-compose.yml`'s `kafka` service advertised a single listener as `localhost:9092`, which works for host-side clients but breaks container-to-container traffic (a container's initial bootstrap to `kafka:9092` succeeds, but Kafka's own metadata then tells it to reconnect to `localhost:9092`, which resolves to itself, not the `kafka` container). Fixed by splitting into two listeners: `PLAINTEXT` for container-to-container traffic (advertised as `kafka:9092`) and `PLAINTEXT_HOST` for host-side traffic (advertised as `localhost`, on the existing `KAFKA_PORT`).

### Learned
<!-- TODO: do NOT fill this in. The user must fill this in themselves, in their own words, after reviewing what was actually built. -->

### Blockers / questions to raise
- A handful of scraped reviews contain literal NUL bytes (`0x00`) inside their `content` field on real Play Store data (observed in Persian-language reviews) — Postgres text/varchar columns can never store `0x00`, so these are permanently unwritable, not a transient failure. The consumer's current behavior (log, skip, leave unacked for redelivery) is correct per spec, but a message like this fails and gets redelivered forever rather than eventually succeeding; worth deciding whether a dead-letter mechanism or content sanitization is needed as the review volume grows.
- 9 of the 16 apps in the currently running `sahabino` database still have placeholder `package_name` values (`com.placeholder.*`), even though earlier days' logs describe these as corrected — this environment's data doesn't reflect those fixes, which is why only 7 of 16 apps produced stats/reviews in both of today's passes. Not something `storage-consumer` can or should fix (that data is owned by `app-list-api-fastapi`), but the seed script should be re-run against this environment before relying on it for anything beyond today's pipeline smoke test.
- Confirmed still open from Day 4: `app-list-api-fastapi`/`-django` have no Docker healthcheck, so `playstore-scraper`'s first scrape pass raced uvicorn's startup again today after the containers were recreated, and had to be restarted manually to trigger a real pass.

### Plan for tomorrow
- Day 7 is a non-coding day per the roadmap: learn Wireshark fundamentals and capture pcap files for Baham and Pinno, laying the groundwork for the network-traffic-analysis work planned after the scraping/storage pipeline.
