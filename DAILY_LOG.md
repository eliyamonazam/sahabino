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
