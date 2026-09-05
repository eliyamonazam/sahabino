from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AppCategory = Literal["messenger", "operator", "video", "word_game", "chat_dating", "social"]


class AppCreate(BaseModel):
    package_name: str = Field(
        ...,
        max_length=255,
        description="Google Play package id, e.g. 'org.telegram.messenger'. Must be unique.",
        examples=["org.telegram.messenger"],
    )
    name: str = Field(
        ...,
        max_length=255,
        description="Human-readable display name of the app, e.g. 'Telegram'.",
        examples=["Telegram"],
    )
    category: AppCategory = Field(
        ...,
        description=(
            "App category. One of: messenger, operator, video, word_game, "
            "chat_dating, social."
        ),
        examples=["messenger"],
    )


class AppUpdate(BaseModel):
    package_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="New Google Play package id. Omit to leave the current value unchanged. Must be unique.",
    )
    name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="New display name. Omit to leave the current value unchanged.",
    )
    category: Optional[AppCategory] = Field(
        default=None,
        description=(
            "New category. Omit to leave the current value unchanged. One of: "
            "messenger, operator, video, word_game, chat_dating, social."
        ),
    )


class AppRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal numeric id of the app.")
    package_name: str = Field(..., description="Google Play package id.")
    name: str = Field(..., description="Human-readable display name of the app.")
    category: str = Field(..., description="App category.")
    is_active: bool = Field(..., description="Whether the app is actively tracked (soft-delete flag).")
    created_at: datetime = Field(..., description="Timestamp when this row was created.")
    updated_at: datetime = Field(..., description="Timestamp when this row was last updated.")
