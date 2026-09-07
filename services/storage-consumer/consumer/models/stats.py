from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from consumer.database import Base


class AppStatsSnapshot(Base):
    """One row per scrape of an app's Play Store stats.

    Intentionally append-only: a new row is inserted for every stats
    message, never updated in place, so history is preserved for later
    analysis (trend charts, etc.).

    `app_id` is a plain indexed integer, not a foreign key: the `apps` table
    it logically references is owned by app-list-api-fastapi's own Alembic
    history, and a cross-service FK would couple the two services'
    independent migrations together. See the README for more on this.
    """

    __tablename__ = "app_stats_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    min_installs: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratings: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reviews_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    store_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ad_supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
