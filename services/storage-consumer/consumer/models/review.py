from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from consumer.database import Base


class Review(Base):
    """One row per unique Play Store review, upserted over time by review_id.

    `first_seen_at` is set once, on first insert, and never touched again.
    `last_seen_at` is bumped on every write (insert or update), so it marks
    the most recent scrape pass that still saw this review. `sentiment` is
    unused for now (populated by a future analysis job); the upsert
    deliberately never overwrites it with NULL on a re-scrape.

    `app_id` is a plain indexed integer, not a foreign key -- see the same
    note on AppStatsSnapshot for why this service never adds cross-service
    FKs to the `apps` table.
    """

    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thumbs_up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
