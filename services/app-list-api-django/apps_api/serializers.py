from rest_framework import serializers

from .models import CATEGORY_CHOICES, App


class AppSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(
        max_length=255,
        help_text="Google Play package id, e.g. 'org.telegram.messenger'. Must be unique.",
    )
    name = serializers.CharField(
        max_length=255,
        help_text="Human-readable display name of the app, e.g. 'Telegram'.",
    )
    category = serializers.ChoiceField(
        choices=CATEGORY_CHOICES,
        help_text="App category. One of: messenger, operator, video, word_game, chat_dating, social.",
    )

    class Meta:
        model = App
        fields = ["id", "package_name", "name", "category", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]
