"""Validates and shapes raw broker payloads into the dicts the persistence
layer writes to Postgres. Kept separate from persistence so a malformed
payload can be rejected before any DB call is made.
"""

from datetime import UTC, datetime
from typing import Any


class InvalidMessageError(ValueError):
    """Raised when a broker payload is missing a required field or is malformed."""


def _require(payload: dict[str, Any], field: str) -> Any:
    value = payload.get(field)
    if value is None:
        raise InvalidMessageError(f"Missing required field '{field}'")
    return value


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse a timestamp that may arrive as an ISO string or a Unix epoch number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise InvalidMessageError(f"Invalid timestamp value: {value!r}") from exc
    raise InvalidMessageError(f"Invalid timestamp value: {value!r}")


def parse_stats_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a playstore-app-stats payload and shape it for insert_stats_snapshot.

    Raises InvalidMessageError if app_id or scraped_at (used as fetched_at)
    is missing or malformed.
    """
    app_id = _require(payload, "app_id")
    fetched_at = _parse_timestamp(_require(payload, "scraped_at"))

    return {
        "app_id": app_id,
        "min_installs": payload.get("min_installs"),
        "score": payload.get("score"),
        "ratings": payload.get("ratings"),
        "reviews_count": payload.get("reviews"),
        "store_updated_at": _parse_timestamp(payload.get("store_last_updated")),
        "version": payload.get("version"),
        "ad_supported": payload.get("ad_supported"),
        "fetched_at": fetched_at,
    }


def parse_review_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a playstore-app-reviews payload and shape it for upsert_review.

    Raises InvalidMessageError if review_id or app_id is missing.
    """
    review_id = _require(payload, "review_id")
    app_id = _require(payload, "app_id")

    return {
        "review_id": review_id,
        "app_id": app_id,
        "at": _parse_timestamp(payload.get("at")),
        "user_name": payload.get("user_name"),
        "thumbs_up_count": payload.get("thumbs_up_count"),
        "score": payload.get("score"),
        "content": payload.get("content"),
    }
