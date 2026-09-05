import pytest
from django.db import connection

# This table is managed = False (see apps_api.models.App) — its schema is
# owned by the app-list-api-fastapi service's Alembic migrations, so
# Django's own migrate/test-db setup will never create it. This DDL is
# copied by hand from services/app-list-api-fastapi/alembic/versions/
# a8912659b621_create_apps_table.py and must be kept in sync manually if
# that migration ever changes.
CREATE_APPS_TABLE_SQL = """
CREATE TABLE apps (
    id SERIAL PRIMARY KEY,
    package_name VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ix_apps_package_name ON apps (package_name);
COMMENT ON COLUMN apps.category IS
    'One of: messenger, operator, video, word_game, chat_dating, social';
"""

DROP_APPS_TABLE_SQL = "DROP TABLE IF EXISTS apps;"


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute(CREATE_APPS_TABLE_SQL)
    yield
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute(DROP_APPS_TABLE_SQL)
