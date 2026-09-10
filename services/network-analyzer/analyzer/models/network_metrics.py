from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from analyzer.database import Base


class NetworkMetrics(Base):
    """One row per analyzed pcap file.

    `app_id` is a plain indexed integer, not a foreign key: the `apps` table
    it logically references belongs to app-list-api-fastapi's own Alembic
    history, and a cross-service FK would couple the two services'
    independent migrations together (same convention as storage-consumer's
    `app_stats_snapshots`/`reviews`, see its README for more on this).

    `source_file` is the natural dedup key: a pcap file is analyzed at most
    once, so re-running the tool over a directory that mixes old and newly
    added files only processes the new ones.
    """

    __tablename__ = "network_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scenario: Mapped[str] = mapped_column(String(10), nullable=False)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    handshake_rtt_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    retransmission_count: Mapped[int] = mapped_column(Integer, nullable=False)
    zero_window_event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    tcp_reset_drops: Mapped[int] = mapped_column(Integer, nullable=False)
    total_transferred_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_payload_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    overhead_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
