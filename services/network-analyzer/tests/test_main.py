"""Exercises _process_file's skip/analyze decision directly (unmatched app
name, dedup by source_file, and the happy path), rather than through a real
AppListClient or a directory scan.
"""

import shutil
from datetime import UTC, datetime

from analyzer.main import _process_file
from analyzer.models.network_metrics import NetworkMetrics
from analyzer.persistence import insert_network_metrics
from sqlalchemy import select

from tests.conftest import SAMPLE_PCAP


def _copy_fixture(tmp_path, filename: str):
    """sample.pcap itself doesn't follow the {app}_{scenario}_{NN}.pcap naming
    convention, so tests that exercise filename-based behavior work off a
    renamed copy instead of the checked-in fixture file.
    """
    destination = tmp_path / filename
    shutil.copy(SAMPLE_PCAP, destination)
    return destination


async def test_unmatched_app_name_is_skipped_without_inserting(session_factory, tmp_path, caplog):
    pcap_path = _copy_fixture(tmp_path, "unknownapp_send_01.pcap")

    await _process_file(pcap_path, apps_by_name={}, session_factory=session_factory)

    async with session_factory() as session:
        rows = (await session.execute(select(NetworkMetrics))).scalars().all()
    assert rows == []
    assert "no tracked app matches name" in caplog.text


async def test_already_analyzed_file_is_skipped(session_factory, tmp_path):
    pcap_path = _copy_fixture(tmp_path, "testapp_send_01.pcap")
    apps_by_name = {"testapp": {"id": 7, "name": "Testapp"}}

    async with session_factory() as session:
        await insert_network_metrics(
            session,
            {
                "app_id": 7,
                "scenario": "send",
                "source_file": "testapp_send_01.pcap",
                "handshake_rtt_ms": 1.0,
                "retransmission_count": 0,
                "zero_window_event_count": 0,
                "tcp_reset_drops": 0,
                "total_transferred_bytes": 10,
                "total_payload_bytes": 5,
                "overhead_ratio": 0.5,
                "analyzed_at": datetime.now(UTC),
            },
        )

    await _process_file(pcap_path, apps_by_name, session_factory)

    async with session_factory() as session:
        rows = (await session.execute(select(NetworkMetrics))).scalars().all()
    # still just the one pre-existing row: _process_file must not have
    # re-analyzed and inserted a second row for the same source_file.
    assert len(rows) == 1


async def test_matched_app_and_new_file_is_analyzed_and_stored(session_factory, tmp_path):
    pcap_path = _copy_fixture(tmp_path, "testapp_receive_02.pcap")
    apps_by_name = {"testapp": {"id": 9, "name": "Testapp"}}

    await _process_file(pcap_path, apps_by_name, session_factory)

    async with session_factory() as session:
        rows = (await session.execute(select(NetworkMetrics))).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.app_id == 9
    assert row.scenario == "receive"
    assert row.source_file == "testapp_receive_02.pcap"
    assert row.retransmission_count == 1
    assert row.zero_window_event_count == 1
    assert row.tcp_reset_drops == 1
    assert row.total_transferred_bytes == 480
    assert row.total_payload_bytes == 200
