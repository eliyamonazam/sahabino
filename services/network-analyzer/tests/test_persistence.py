from datetime import UTC, datetime

from analyzer.persistence import insert_network_metrics, source_file_already_analyzed


def make_metrics_values(**overrides) -> dict:
    values = {
        "app_id": 1,
        "scenario": "send",
        "source_file": "baham_send_01.pcap",
        "handshake_rtt_ms": 12.5,
        "retransmission_count": 0,
        "zero_window_event_count": 0,
        "tcp_reset_drops": 0,
        "total_transferred_bytes": 1000,
        "total_payload_bytes": 900,
        "overhead_ratio": 0.1,
        "analyzed_at": datetime.now(UTC),
    }
    values.update(overrides)
    return values


async def test_source_file_already_analyzed_is_false_for_unseen_file(session_factory):
    async with session_factory() as session:
        assert await source_file_already_analyzed(session, "never_seen.pcap") is False


async def test_source_file_already_analyzed_is_true_after_insert(session_factory):
    async with session_factory() as session:
        await insert_network_metrics(session, make_metrics_values())

    async with session_factory() as session:
        assert await source_file_already_analyzed(session, "baham_send_01.pcap") is True
        assert await source_file_already_analyzed(session, "baham_send_02.pcap") is False
