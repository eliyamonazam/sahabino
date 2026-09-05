"""
Django settings for the app-list-api-django service.

This is a pure JSON API service reading/writing a table it does not own the
schema of (see apps_api.models.App, managed = False) — INSTALLED_APPS and
MIDDLEWARE are trimmed to what that actually requires, rather than the full
django-admin default (no admin site, sessions, or auth app).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Loading the repo-root .env is a convenience for running this service
# outside of docker compose (e.g. from a local venv). Inside docker compose,
# environment variables are already injected and this file won't exist at
# this relative path, so it's a no-op there.
_parents = BASE_DIR.resolve().parents
if len(_parents) > 1 and (_parents[1] / ".env").exists():
    load_dotenv(_parents[1] / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-only-key-not-for-production")

DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = ["*"]


INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps_api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
#
# Connection info is read from the same POSTGRES_* environment variables used
# by the app-list-api-fastapi service (the shared repo-root .env), so both
# services point at the exact same database.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "sahabino"),
        "USER": os.getenv("POSTGRES_USER", "sahabino"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "changeme"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "TEST": {
            # A database name distinct from the FastAPI service's
            # sahabino_test, so the two services' independent test suites
            # never collide or share a lifecycle.
            "NAME": os.getenv("POSTGRES_TEST_DB_DJANGO", "sahabino_test_django"),
        },
    }
}


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    # No session/auth apps are installed (see MIDDLEWARE above); this is an
    # unauthenticated internal service, same as the FastAPI implementation.
    # UNAUTHENTICATED_USER must be None (not DRF's default AnonymousUser),
    # since that default lazily imports django.contrib.auth.models, which
    # requires the auth app to be in INSTALLED_APPS.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "App List API (Django)",
    "DESCRIPTION": "CRUD API for managing the list of Google Play apps to be tracked.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
