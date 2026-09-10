# app-list-api-django

Django + Django REST Framework implementation of the app-list CRUD API (shares a database with the FastAPI implementation).

This service reads and writes the same `apps` table as `app-list-api-fastapi`, but **does not own its schema**. The `App` model (`apps_api/models.py`) is declared `managed = False`, so `python manage.py migrate` will never create, alter, or drop this table — the FastAPI service's Alembic migrations remain the single source of truth for the table's schema.

## Endpoints

- `POST /apps/` — create an app (`package_name`, `name`, `category`). 409 if `package_name` already exists.
- `GET /apps/?active_only=false` — list apps, optionally filtered to active ones.
- `PATCH /apps/{id}/` — partially update `package_name`, `name`, and/or `category`. 404 if not found; 409 if the new `package_name` collides with another row.
- `DELETE /apps/{id}/` — soft delete: sets `is_active = false`. 404 if not found.
- `GET /health/` — 200 if the database is reachable (runs `SELECT 1`), 503 if not. Used by the Docker healthcheck.

Interactive docs (Swagger UI) are served at `/api/schema/swagger-ui/` once the service is running.

## Configuration

Connection info is read from the same `POSTGRES_*` environment variables as `app-list-api-fastapi` (the shared repo-root `.env` / `.env.example`):

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- `POSTGRES_TEST_DB_DJANGO` — test database name (default `sahabino_test_django`), deliberately distinct from the FastAPI service's `sahabino_test` so the two services' test suites never share a lifecycle.

Host-side Postgres is on port `5433` (not `5432`), same as the FastAPI service — see its README for why.

When run via `docker compose`, `POSTGRES_HOST` is overridden to `postgres`; when run locally outside Docker it defaults to `localhost`.

## Running locally (outside Docker)

```bash
python -m venv .venv
source .venv/Scripts/activate   # .venv/bin/activate on Linux/macOS
pip install -r requirements-dev.txt

# Make sure postgres is up (from the repo root): docker compose up -d postgres

python manage.py migrate       # safe: skips the unmanaged `apps` table, just sets up Django's own bookkeeping tables
python manage.py runserver 8002
```

## Migrations

`python manage.py makemigrations apps_api` records model state changes as normal, but `migrate` will never touch the actual `apps` table (see `managed = False` above). If the FastAPI service's Alembic migration for this table ever changes, update `apps_api/models.py` (and `conftest.py`'s test DDL, see below) to match by hand.

## Tests

Because the `apps` table is unmanaged, Django's test runner won't create it in the test database — there's nothing for it to create as far as Django is concerned. `conftest.py` overrides pytest-django's `django_db_setup` fixture to run the same `CREATE TABLE apps (...)` DDL used by the FastAPI service's initial Alembic migration directly against the test database before the session, and drops it after.

```bash
pytest
```

## Docker

Built and run as the `app-list-api-django` service in the root `docker-compose.yml`, exposed on `APP_LIST_API_DJANGO_PORT` (default `8002`). It depends only on `postgres` being healthy — it does not depend on `app-list-api-fastapi`; the two services are independent, both just reading/writing the same table.
