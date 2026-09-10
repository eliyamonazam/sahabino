# app-list-api-fastapi

FastAPI implementation of the app-list CRUD API (shares a database with the Django implementation). This service owns the Alembic migrations for the `apps` table — the Django implementation reads the same table but does not manage its schema.

## Endpoints

- `POST /apps` — create an app (`package_name`, `name`, `category`). 409 if `package_name` already exists.
- `GET /apps?active_only=false` — list apps, optionally filtered to active ones.
- `PATCH /apps/{id}` — partially update `package_name`, `name`, and/or `category`. 404 if not found; 409 if the new `package_name` is already used by another row.
- `DELETE /apps/{id}` — soft delete: sets `is_active = false`. 404 if not found.
- `GET /health` — 200 if the database is reachable (runs `SELECT 1`), 503 if not. Used by the Docker healthcheck.

Interactive docs (Swagger UI) are served at `/docs` once the service is running.

## Configuration

Connection info is read from environment variables — the same `POSTGRES_*` variables defined in the repo root `.env` / `.env.example`:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` — used to build an `postgresql+asyncpg://...` URL.
- `DATABASE_URL` — if set, overrides the constructed URL entirely.
- `POSTGRES_TEST_DB` — database name used by the test suite (default `sahabino_test`), on the same Postgres instance.

When run via `docker compose`, `POSTGRES_HOST` is overridden to `postgres` (the service name); when run locally outside Docker it defaults to `localhost`.

Note: the host-side Postgres port is `5433`, not the default `5432` (see `POSTGRES_PORT` in `.env.example`) — this avoids colliding with a locally installed Postgres server that some machines already have listening on `5432`. This only affects connections made directly from the host (a local venv's `alembic`/`pytest`, a host-side `psql`); containers on the docker compose network still reach postgres on its internal `5432`.

## Running locally (outside Docker)

```bash
python -m venv .venv
source .venv/Scripts/activate   # .venv/bin/activate on Linux/macOS
pip install -r requirements-dev.txt

# Make sure postgres is up (from the repo root): docker compose up -d postgres
# It's reachable from the host at localhost:5433 (see the note above).

alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Tests

Tests run against a separate database (`POSTGRES_TEST_DB`, default `sahabino_test`) on the same Postgres instance, created/dropped automatically by the test fixtures — they do not touch the real `sahabino` database.

```bash
# one-time: create the test database on the running postgres instance
docker compose exec postgres createdb -U sahabino sahabino_test

pytest
```

## Docker

Built and run as the `app-list-api-fastapi` service in the root `docker-compose.yml`, exposed on `APP_LIST_API_FASTAPI_PORT` (default `8001`). The container entrypoint runs `alembic upgrade head` before starting `uvicorn`.
