"""Extracts the 7 network-quality metrics from a single pcap file, using the
exact filters defined in the Day 7 capture guide.

pyshark shells out to the real `tshark` binary and streams its packet
dissection back as JSON, so each of these fields is tshark's own analysis
(retransmission/zero-window detection, per-stream RTT tracking, etc.), not
something recomputed here.
"""

import asyncio
from typing import Any

import pyshark


def _ensure_event_loop() -> None:
    """pyshark needs an asyncio event loop set on the calling thread.

    This is a synchronous, single-threaded batch tool, so there's normally
    no loop running yet; some Python versions no longer create one
    implicitly for a synchronous caller, so one is created and set here if
    none exists.
    """
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _is_true(field: Any) -> bool:
    # pyshark represents tshark's boolean fields (e.g. tcp.flags.reset) as
    # the literal strings "True"/"False", not as Python bools or "0"/"1".
    return str(field) == "True"


def _average_first_value_per_stream(entries: list[tuple[str, float]]) -> float | None:
    """Average the first value seen for each stream id in `entries`.

    Used for handshake_rtt_ms: `entries` is (tcp.stream, tcp.analysis.ack_rtt)
    pairs, one per SYN+ACK packet in the file. A plain average across every
    SYN+ACK packet would let a connection that retried its handshake
    contribute one value per retry instead of one value for the connection,
    over-weighting exactly the unstable connections this metric is meant to
    characterize. Keeping only the first value per stream (the initial
    handshake attempt, not a retry) gives one RTT per connection regardless
    of how many SYN+ACK packets that connection's stream contains.
    """
    first_by_stream: dict[str, float] = {}
    for stream_id, value in entries:
        if stream_id not in first_by_stream:
            first_by_stream[stream_id] = value

    if not first_by_stream:
        return None
    values = list(first_by_stream.values())
    return sum(values) / len(values)


def extract_metrics(pcap_path: str) -> dict[str, Any]:
    """Extract the 7 network-quality metrics from one pcap file.

    - handshake_rtt_ms: average tcp.analysis.ack_rtt (converted to ms) across
      SYN+ACK packets, one value per TCP connection (tcp.stream) - see
      _average_first_value_per_stream above for why this isn't a flat
      per-packet average.
    - retransmission_count: packets matching tcp.analysis.retransmission.
    - zero_window_event_count: packets matching tcp.analysis.zero_window.
    - tcp_reset_drops: packets matching tcp.flags.reset==1.
    - total_transferred_bytes: sum of frame.len across all packets.
    - total_payload_bytes: sum of tcp.len across packets where tcp.len > 0.
    - overhead_ratio: (total_transferred - total_payload) / total_transferred.

    handshake_rtt_ms and overhead_ratio are None when the file has no
    SYN+ACK packet / no traffic at all, rather than a misleading 0.
    """
    _ensure_event_loop()

    total_transferred_bytes = 0
    total_payload_bytes = 0
    retransmission_count = 0
    zero_window_event_count = 0
    tcp_reset_drops = 0
    ack_rtt_entries: list[tuple[str, float]] = []

    capture = pyshark.FileCapture(pcap_path, keep_packets=False)
    try:
        for packet in capture:
            total_transferred_bytes += int(packet.length)

            if not hasattr(packet, "tcp"):
                continue
            tcp = packet.tcp

            tcp_len = int(tcp.len)
            if tcp_len > 0:
                total_payload_bytes += tcp_len

            if hasattr(tcp, "analysis_retransmission"):
                retransmission_count += 1
            if hasattr(tcp, "analysis_zero_window"):
                zero_window_event_count += 1
            if _is_true(tcp.flags_reset):
                tcp_reset_drops += 1
            if _is_true(tcp.flags_syn) and _is_true(tcp.flags_ack) and hasattr(tcp, "analysis_ack_rtt"):
                ack_rtt_entries.append((str(tcp.stream), float(tcp.analysis_ack_rtt)))
    finally:
        capture.close()

    average_ack_rtt = _average_first_value_per_stream(ack_rtt_entries)
    handshake_rtt_ms = average_ack_rtt * 1000 if average_ack_rtt is not None else None
    overhead_ratio = (
        (total_transferred_bytes - total_payload_bytes) / total_transferred_bytes
        if total_transferred_bytes
        else None
    )

    return {
        "handshake_rtt_ms": handshake_rtt_ms,
        "retransmission_count": retransmission_count,
        "zero_window_event_count": zero_window_event_count,
        "tcp_reset_drops": tcp_reset_drops,
        "total_transferred_bytes": total_transferred_bytes,
        "total_payload_bytes": total_payload_bytes,
        "overhead_ratio": overhead_ratio,
    }
