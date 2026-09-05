from django.db import models

# Allowed values for `category` (enforced in the serializer, not the DB,
# since more categories may be added over time). Kept in sync by hand with
# the equivalent constant in the FastAPI service's app/schemas/app.py.
CATEGORY_CHOICES = ["messenger", "operator", "video", "word_game", "chat_dating", "social"]


class App(models.Model):
    """A tracked Google Play app.

    This table's schema is owned by the app-list-api-fastapi service's
    Alembic migrations, not by Django — managed = False means Django will
    never create, alter, or drop this table via migrate.
    """

    # Explicit AutoField (32-bit), not BigAutoField (the project default) —
    # the real `id` column, created by the FastAPI service's Alembic
    # migration, is a plain Postgres `integer`, not `bigint`.
    id = models.AutoField(primary_key=True)
    package_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Google Play package id, e.g. 'org.telegram.messenger'.",
    )
    name = models.CharField(max_length=255, help_text="Human-readable display name of the app.")
    category = models.CharField(
        max_length=50,
        help_text="App category. One of: messenger, operator, video, word_game, chat_dating, social.",
    )
    is_active = models.BooleanField(default=True, help_text="Whether the app is actively tracked (soft-delete flag).")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when this row was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when this row was last updated.")

    class Meta:
        db_table = "apps"
        managed = False

    def __str__(self) -> str:
        return self.package_name
