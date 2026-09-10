"""Writes analyzed pcap metrics to Postgres, and answers the dedup check
that keeps re-running the tool over a directory idempotent.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analyzer.models.network_metrics import NetworkMetrics


async def source_file_already_analyzed(session: AsyncSession, source_file: str) -> bool:
    result = await session.execute(select(NetworkMetrics.id).where(NetworkMetrics.source_file == source_file))
    return result.scalar_one_or_none() is not None


async def insert_network_metrics(session: AsyncSession, values: dict[str, Any]) -> None:
    session.add(NetworkMetrics(**values))
    await session.commit()
