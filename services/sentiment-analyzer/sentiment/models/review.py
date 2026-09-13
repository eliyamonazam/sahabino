from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sentiment.database import Base


class Review(Base):
    """A partial mapping of the `reviews` table.

    This table's schema is owned by storage-consumer's own Alembic history
    (see services/storage-consumer/consumer/models/review.py for the full
    column set) -- this service only reads/writes the columns it actually
    needs and never runs migrations of its own against it. Since
    `Base.metadata.create_all` is only ever used by this service's own test
    suite (against a table built from hand-copied DDL, not this class), an
    incomplete column set here is safe: it never drives real schema creation.
    """

    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
