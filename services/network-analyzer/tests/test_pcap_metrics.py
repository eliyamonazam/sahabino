"""Exercises extract_metrics against two small, hand-crafted pcap fixtures:

- tests/fixtures/sample.pcap: SYN, SYN-ACK, ACK, one 100-byte data packet, an
  identical retransmission of it, a zero-window ACK, and a RST - one
  connection, single-value RTT.
- tests/fixtures/multi_stream_handshakes.pcap: two connections; the first
  connection's SYN-ACK is itself retransmitted once before the handshake
  completes, the second connection's handshake is clean.

Expected values for both were confirmed independently with
`tshark -Y <filter>` against the same files, not derived from this module.
"""

from analyzer.pcap_metrics import _average_first_value_per_stream, extract_metrics

from tests.conftest import MULTI_STREAM_HANDSHAKES_PCAP, SAMPLE_PCAP


def test_extract_metrics_matches_known_values():
    metrics = extract_metrics(str(SAMPLE_PCAP))

    assert metrics["handshake_rtt_ms"] == 10.0
    assert metrics["retransmission_count"] == 1
    assert metrics["zero_window_event_count"] == 1
    assert metrics["tcp_reset_drops"] == 1
    assert metrics["total_transferred_bytes"] == 480
    assert metrics["total_payload_bytes"] == 200
    assert metrics["overhead_ratio"] == (480 - 200) / 480


def test_extract_metrics_averages_rtt_per_connection_not_per_packet():
    """One connection has a retransmitted SYN-ACK, the other doesn't.

    tshark itself never assigns tcp.analysis.ack_rtt to a packet it's
    flagged as a retransmission (confirmed against this and several other
    constructed captures), so this particular file's RTT average happens to
    come out the same whether or not the retry is deduplicated - a plain
    per-packet average would only diverge from the per-connection one on a
    file where more than one *valid, non-retransmission-flagged* SYN+ACK
    lands on the same tcp.stream, which none of the 8 real captures this
    service has been validated against contain either. This still exercises
    the real grouping-by-stream code path end to end (two connections'
    values correctly kept separate and averaged as two, not conflated into
    one or three); test_average_first_value_per_stream_ignores_later_values_for_the_same_stream
    below is the direct regression guard for the double-counting bug itself.
    """
    metrics = extract_metrics(str(MULTI_STREAM_HANDSHAKES_PCAP))

    assert metrics["handshake_rtt_ms"] == (10.0 + 20.0) / 2
    assert metrics["retransmission_count"] == 1
    assert metrics["zero_window_event_count"] == 0
    assert metrics["tcp_reset_drops"] == 0
    assert metrics["total_transferred_bytes"] == 280
    assert metrics["total_payload_bytes"] == 0
    assert metrics["overhead_ratio"] == 1.0


def test_average_first_value_per_stream_ignores_later_values_for_the_same_stream():
    # stream "0" has two entries (e.g. an original SYN-ACK and a later,
    # slower retry); only the first (10ms) should count. stream "1" has one
    # entry (20ms). A naive flat average of all three raw values would be
    # (10 + 60 + 20) / 3 = 30; grouped by stream it's (10 + 20) / 2 = 15.
    entries = [("0", 0.010), ("1", 0.020), ("0", 0.060)]

    assert _average_first_value_per_stream(entries) == (0.010 + 0.020) / 2


def test_average_first_value_per_stream_returns_none_for_no_entries():
    assert _average_first_value_per_stream([]) is None
