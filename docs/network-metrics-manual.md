# Manual Network Metrics — Day 7 Reference

Extracted manually with tshark/Wireshark from real pcap captures (Baham & Pinno, send/receive scenarios,
2 repetitions each). These values are used to cross-check the `network-analyzer` service's automated output
built on Day 8 — they should match closely.

Capture note: PCAPdroid captures at the IP layer (`Raw IP` encapsulation, no Ethernet header), since it works
via a local VPN service rather than a real network interface. Overhead Ratio here is therefore slightly lower
than it would be from a capture that includes Ethernet framing.

| File | Handshake RTT (ms) | # connections | Retransmissions | Zero Window | TCP Resets | Total Bytes | Payload Bytes | Overhead % |
|---|---|---|---|---|---|---|---|---|
| baham_receive_01 | 63.0 | 9 | 0 | 0 | 0 | 7,658,091 | 7,572,571 | 1.1% |
| baham_receive_02 | 57.0 | 27 | 0 | 0 | 7 | 12,968,991 | 12,827,325 | 1.1% |
| baham_send_01 | 718.2 | 21 | 15 | 0 | 13 | 18,607,842 | 18,470,654 | 0.7% |
| baham_send_02 | 376.9 | 28 | 2 | 0 | 9 | 14,382,058 | 14,286,360 | 0.7% |
| pinno_receive_01 | 27.9 | 17 | 0 | 0 | 10 | 1,400,649 | 1,347,307 | 3.8% |
| pinno_receive_02 | 28.1 | 14 | 0 | 0 | 8 | 8,088,540 | 7,979,084 | 1.4% |
| pinno_send_01 | 514.9 | 38 | 12 | 0 | 36 | 13,548,546 | 13,344,566 | 1.5% |
| pinno_send_02 | 326.7 | 116 | 207 | 0 | 125 | 68,970,744 | 67,024,709 | 2.8% |

## Observations

- **Send scenarios consistently show higher RTT, more retransmissions, and more resets than receive scenarios** —
  consistent with mobile uplink typically being slower/less reliable than downlink.
- **Zero Window is 0 across every file** — buffers never filled up during these tests; file sizes were small
  enough relative to modern network throughput.
- **High reset counts (notably `pinno_send_02`) are not necessarily a sign of a bad connection** — mobile apps
  commonly close parallel/completed TCP connections with RST instead of a full FIN handshake, especially during
  multi-connection uploads. This needs interpretation, not just raw counting.
