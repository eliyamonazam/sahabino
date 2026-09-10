# network-analyzer

Analyzes manually captured pcap files (Wireshark/`tshark` traffic captures,
one per app + scenario) and extracts the project's 7 network-quality
metrics into Postgres.

Unlike `playstore-scraper`/`storage-consumer`, this isn't a long-running
daemon: pcap files show up occasionally from manual capture, not as a
continuous stream, so this is a **batch CLI tool** (`python -m
analyzer.main`) that processes every `.pcap` file in a directory once and
exits. It's meant to be run with `docker compose run --rm
network-analyzer`, not brought up with the rest of the stack via `up -d`.

## How it works

1. Fetches every tracked app (active or not) from `app-list-api-fastapi`
   (`GET /apps`) - the same "FastAPI is the source of truth for the app
   list" pattern `playstore-scraper` follows, except unfiltered by
   `active_only`, since a pcap capture may reference an app that's since
   been deactivated but still needs its metrics attributed correctly.
2. For each `.pcap` file in the target directory (default `PCAP_DIR`, see
   Configuration):
   - Parses the app name and scenario out of its filename
     (`{app_name}_{send|receive}_{NN}.pcap`, e.g. `baham_send_01.pcap`;
     `analyzer/filename_parser.py`). A filename that doesn't match this
     convention is logged as a warning and skipped.
   - Looks up the parsed app name (case-insensitive) against the tracked
     apps fetched in step 1. No match is logged as a warning and skipped.
   - Skips the file if a row for it (by `source_file`) already exists -
     see Schema below. This is the dedup check that makes re-running the
     tool against a directory that's gained new files since the last run
     safe, without reprocessing everything.
   - Otherwise extracts the 7 metrics (`analyzer/pcap_metrics.py`, see
     Metrics below) and inserts one row into `network_metrics`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `APP_LIST_API_URL` | `http://app-list-api-fastapi:8000` | Base URL of the app-list-api-fastapi service |
| `PCAP_DIR` | `data/pcap-samples` | Directory of `.pcap` files to process, when none is given as a CLI argument. Resolved relative to the current working directory (the repo root, both locally and in the container). |

The directory can also be passed explicitly: `python -m analyzer.main
/some/other/dir` overrides `PCAP_DIR` for that run.

## Metrics

Extracted with [pyshark](https://github.com/KimiNewt/pyshark) (a thin
wrapper that shells out to the real `tshark` binary, so these are tshark's
own packet-analysis filters, not something recomputed here), exactly as
defined in the Day 7 capture guide:

| Metric | Filter |
|---|---|
| `handshake_rtt_ms` | Average `tcp.analysis.ack_rtt` (converted to ms), one value per TCP connection (`tcp.stream`) |
| `retransmission_count` | Count of packets matching `tcp.analysis.retransmission` |
| `zero_window_event_count` | Count of packets matching `tcp.analysis.zero_window` |
| `tcp_reset_drops` | Count of packets matching `tcp.flags.reset==1` |
| `total_transferred_bytes` | Sum of `frame.len` across all packets |
| `total_payload_bytes` | Sum of `tcp.len` across packets where `tcp.len > 0` |
| `overhead_ratio` | `(total_transferred_bytes - total_payload_bytes) / total_transferred_bytes` |

`handshake_rtt_ms` and `overhead_ratio` are stored as `NULL` rather than 0
for a file with no SYN+ACK packet / no traffic at all.

`handshake_rtt_ms` is averaged per connection rather than per packet: for
each `tcp.stream` that has one or more SYN+ACK packets, only the RTT from
the *first* one is kept (the initial handshake attempt, not a retry), and
those one-per-connection values are what gets averaged
(`analyzer/pcap_metrics.py:_average_first_value_per_stream`). A flat
average across every SYN+ACK packet would let a connection that retried
its handshake contribute one value per retry, over-weighting exactly the
unstable connections this metric exists to characterize.

**`handshake_rtt_ms` is sensitive to the exact tshark version.** tshark's
own completeness heuristic for `tcp.analysis.ack_rtt` changed somewhere
between 4.2.x and 4.4.x: on a capture with many concurrent/retried
connections, 4.4.16/4.4.18 leave `ack_rtt` uncomputed for a subset of
SYN-ACK packets that 4.2.2 computes a value for, which measurably shifts
this metric even though every other filter in this table (counts and byte
totals) agrees exactly across versions. This is why the Dockerfile below
is built on Ubuntu 24.04 rather than the Debian-based `python:3.12-slim`
image the other services use, with `tshark` pinned to the exact version
(`4.2.2-1.1build3`) Ubuntu 24.04 ships by default - Debian's own stable
releases jump from 4.0.x (bookworm) straight to 4.4.x (trixie), with no
4.2.x available in either.

## Schema

Owns one table via its own Alembic history (`alembic/versions/`),
independent of the other services':

- **`network_metrics`** - one row per analyzed pcap file. `app_id` is a
  plain indexed integer, not a foreign key, same convention as
  `storage-consumer`'s tables: the `apps` table it logically references is
  owned by `app-list-api-fastapi`'s own migration history, and a
  cross-service FK would couple this service's schema history to that
  other service's. `source_file` (the pcap filename) has a unique index -
  it's the natural dedup key described above, enforced at the database
  level as well as checked before analysis.

## Running migrations

```bash
docker compose run --rm network-analyzer alembic upgrade head
```

(Also runs automatically before `python -m analyzer.main` on every
container start, same as the other services.)

## Tests

Same pattern as the other services: a real Postgres test database
(`POSTGRES_TEST_DB_NETWORK_ANALYZER`, separate from every other service's
test database), no mocking of Postgres itself. Metric-extraction tests run
against small, hand-crafted pcap fixtures instead of a real capture, so
they're deterministic and don't depend on `data/pcap-samples/` (gitignored,
populated only by manual capture):

- `tests/fixtures/sample.pcap` - one connection: SYN, SYN-ACK, ACK, a data
  packet, a retransmission of it, a zero-window ACK, and a RST.
- `tests/fixtures/multi_stream_handshakes.pcap` - two connections, the
  first with its SYN-ACK retransmitted once before the handshake completes.

`_average_first_value_per_stream` (the per-connection RTT averaging logic)
also has its own direct unit tests against plain synthetic
`(stream_id, rtt)` tuples, independent of any pcap file - the most precise
regression guard against reintroducing a flat per-packet average.

Since the image doesn't include the test suite or dev dependencies (kept
out of the runtime image on purpose), run tests with the service directory
bind-mounted over `/app` so `pytest` and `requirements-dev.txt` are both
present as installed/run inside the container that already has `tshark`:

```bash
docker compose run --rm -v "$(pwd)/services/network-analyzer:/app" -e POSTGRES_HOST=postgres network-analyzer \
  sh -c "pip install -r requirements-dev.txt && pytest"
```

or more simply, from a Python 3.12 venv on the host with `tshark` installed
locally, once `POSTGRES_HOST=localhost` is exported to match the port
mapped in `.env`.
