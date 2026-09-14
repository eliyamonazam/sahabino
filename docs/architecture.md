# Architecture

This document consolidates the architecture decisions that were made service-by-service
throughout development (see each service's own `README.md` and `DAILY_LOG.md` for the
original context). Nothing here is new — it's a single place to read the reasoning
without hunting across five services' READMEs and eleven days of logs.

## System overview

The project is really **two independent data pipelines** that happen to write into the
same Postgres instance, plus one standalone batch tool that operates on data already
sitting in that database:

1. **Play Store data pipeline**: `app-list-api-fastapi` (the
   tracked-apps list) → `playstore-scraper` (reads the app list, scrapes the Play
   Store) → Kafka (`playstore-app-stats` / `playstore-app-reviews` topics, via the
   `libs/message_broker` abstraction) → `storage-consumer` (consumes both topics) →
   Postgres (`app_stats_snapshots`, `reviews`).
2. **Network analysis pipeline**: pcap files captured manually with Wireshark/PCAPdroid
   (not by any running service) → `network-analyzer` (a batch tool that reads the pcap
   directory, looks up app names against `app-list-api-fastapi`, and extracts metrics)
   → Postgres (`network_metrics`).
3. **`sentiment-analyzer`**: a standalone batch tool that reads rows already sitting in
   `storage-consumer`'s `reviews` table (`sentiment IS NULL`), classifies them, and
   writes the result back — it depends on data the Play Store pipeline already
   produced, but not on any of that pipeline's services being up at the time it runs.

These three pieces **do not share a message broker and have no runtime dependency on
each other** — pipeline 2 doesn't touch Kafka at all, and `sentiment-analyzer` doesn't
touch Kafka or the app-list APIs. The only thing tying all of it together is that every
service reads/writes the same Postgres instance (each owning its own tables — see
Schema ownership below).

## Per-service responsibility

**`app-list-api-fastapi`** — FastAPI CRUD service for the tracked-apps list (`apps`
table): create, list (with an `active_only` filter), partial update, and soft-delete
(never a hard delete). Always-on (`restart: unless-stopped`), exposed on port 8001,
with Swagger UI at `/docs`. Depends only on Postgres being healthy. It owns the `apps`
table's Alembic migration history — every other service that needs the app list reads
this table's data through this service's schema.

**`playstore-scraper`** — Fetches the current active app list from
`app-list-api-fastapi`, scrapes each app's Play Store listing and recent reviews via
`google-play-scraper`, and publishes one message per stats result and per review onto
Kafka through `libs/message_broker`. Always-on, looping on `SCRAPE_INTERVAL_SECONDS`
(default 3600s). Depends on `app-list-api-fastapi` (healthy) and Kafka (healthy); a
single app's scrape failure is logged and skipped, not fatal to the pass.

**`storage-consumer`** — Consumes both of the scraper's topics via
`libs/message_broker` and persists them into Postgres: an append-only insert per stats
message, an upsert-by-`review_id` for reviews. Always-on, running two concurrent
consume loops (one per topic, each its own consumer group). Depends on Postgres and
Kafka being healthy; it never depends on or calls the app-list APIs directly, since it
only ever reads from the broker.

**`network-analyzer`** — A **batch CLI tool** (`docker compose run --rm
network-analyzer`), not a daemon: pcap files show up occasionally from manual capture,
not as a continuous stream. It fetches the full (unfiltered) app list from
`app-list-api-fastapi`, matches each `.pcap` file's parsed app name against it, extracts
seven network-quality metrics via `pyshark`/`tshark`, and inserts one row per file into
`network_metrics`, skipping files it has already processed (deduped by `source_file`).
Depends on Postgres and (only for the app-list lookup) `app-list-api-fastapi`.

**`sentiment-analyzer`** — Also a **batch CLI tool** (`docker compose run --rm
sentiment-analyzer`), not a daemon: it processes every `reviews` row with `sentiment IS
NULL` once and exits. It depends only on Postgres — it owns no schema of its own, just a
partial mapping of the `reviews` table columns it reads and writes.

**`libs/message_broker`** — Not a deployed service but a shared library used by
`playstore-scraper` and `storage-consumer`: a common `MessageBroker` interface
(`publish`/`consume`/`ack`) with two backend implementations, Redis Streams and Kafka,
selected via `MESSAGE_BROKER_TYPE`. It has no independent lifecycle of its own — it runs
inside whichever service imports it.

> **Note on service count**: the design brief for this document referred to "7
> services." Only five independent services currently live under `services/`
> (`app-list-api-fastapi`, `playstore-scraper`, `storage-consumer`,
> `network-analyzer`, `sentiment-analyzer`); `libs/message_broker`
> is a shared library, not a deployed service, and `postgres`/`kafka`/`metabase` are
> third-party infrastructure containers, not services this project builds. See the
> Part 3 checks at the end of this doc/PR for the same note — flagging it rather than
> inventing more services to match the number.

## Key design decisions

### Schema ownership

Each table has exactly one owner, and ownership is enforced by which service holds the
Alembic (or Django) migration history for it, not just by convention:

- **`apps`** is owned by `app-list-api-fastapi`'s Alembic history — its initial
  migration is the schema's source of truth.
- **`app_stats_snapshots`** and **`reviews`** are owned by `storage-consumer`'s own
  Alembic history.
- **`network_metrics`** is owned by `network-analyzer`'s own Alembic history.
- None of `network_metrics.app_id`, `app_stats_snapshots.app_id`, or `reviews.app_id`
  is a foreign key to `apps.id` — each is a plain indexed integer instead. This is
  deliberate cross-service coupling avoidance: the `apps` table they logically
  reference belongs to a different service's migration history, and a cross-service FK
  would tie that service's schema evolution to another service's, defeating the point
  of each service owning its own tables independently. The reference is enforced at the
  application level instead (each producer only ever emits `app_id` values it obtained
  from `app-list-api-fastapi` in the first place).
- **`storage-consumer` and `app-list-api-fastapi` needed separate Alembic version
  tables** because they share the same Postgres database (not just the same instance),
  and both use Alembic. Alembic's default bookkeeping table (`alembic_version`) has no
  concept of "which service owns this row" — two independent migration histories
  writing to the same `alembic_version` table would collide and corrupt each other's
  "current migration" bookkeeping. Fixed by giving `storage-consumer`'s `alembic/env.py`
  a distinct `version_table` (`alembic_version_storage_consumer`), leaving the default
  table name for `app-list-api-fastapi`. `network-analyzer` follows the same pattern.

### The `MessageBroker` abstraction

`libs/message_broker` exists because the project spec calls for Redis as the default
message broker, with Kafka as a bonus feature — a single `MessageBroker` interface
(`publish`/`consume`/`ack`) with two real implementations (`RedisStreamsBroker`,
`KafkaBroker`) satisfies both without the services that use it (the scraper,
storage-consumer) needing to know or care which backend is active. Backend selection is
a single environment variable, `MESSAGE_BROKER_TYPE`.

The deployed stack later moved to **Kafka-only**: `docker-compose.yml` only runs a
`kafka` container, not `redis`, since the project's bonus criteria frame the choice as
"Kafka instead of Redis," and running two message brokers in parallel indefinitely for
the same job isn't worth the extra always-on service and doubled testing surface. The
Redis implementation and its integration test suite are kept in the codebase rather than
deleted — they demonstrate the same interface working against a genuinely different
backend and required real work to build, so they're a **demonstrated-but-unused
capability**: runnable on demand against a standalone Redis container, just not part of
the stack that's actually up.

### Why `network-analyzer` and `sentiment-analyzer` are batch tools

Unlike the other three services, these two are run via `docker compose run --rm` rather
than being always-on:

- **`network-analyzer`**: pcap files arrive from manual Wireshark/PCAPdroid captures,
  not as a continuous stream — there is no ongoing source for a daemon to watch. The
  tool processes whatever's in the pcap directory once and exits; re-running it against
  a directory that's gained new files since the last run is safe and cheap because of
  the dedup-by-`source_file` check, so there's nothing an always-on process would buy
  over invoking it after each new batch of captures.
- **`sentiment-analyzer`**: it operates on rows that already exist in Postgres
  (`reviews` with `sentiment IS NULL`) rather than reacting to a live event stream —
  there's no queue or topic driving it. It's meant to be run ad hoc after new reviews
  have accumulated, processes the whole backlog in one pass (measured at ~2,800
  reviews/second, the full ~17.5k-row table in about 5 seconds), and exits; idempotency
  comes for free from the `sentiment IS NULL` filter, so a partial or repeated run is
  always safe.

Both explicitly have no `restart` policy in `docker-compose.yml`, so even if they were
accidentally brought up via a bare `docker compose up -d`, they run once and exit rather
than restart-looping.

### Sentiment analysis approach: lexicon over transformer

A pretrained transformer sentiment model (e.g. a ParsBERT sentiment fine-tune) was
considered first and rejected for reasons specific to this project's data and
deployment shape, not sentiment analysis in general:

- **The review text itself doesn't need it.** A manual sample of this project's own
  `reviews` data is dominated by one- or two-word Persian reviews ("عالی", "خوبه",
  "افتضاح"), often with elongated spelling or an emoji standing in for the whole
  review. A lexicon plus a handful of rules (negation, intensifiers,
  character-elongation, emoji) directly targets that structure; a transformer tuned for
  longer, more formal text is arguably overkill for it.
- **Image size and inference cost.** `torch` + `transformers` plus a downloaded model
  checkpoint would take the service's image from ~340MB (`python:3.12-slim` + `hazm` +
  SQLAlchemy/asyncpg, no ML runtime) to multiple GB, and CPU-only inference over ~17.5k
  rows would take meaningfully longer than the lexicon approach's few seconds — a real
  cost for a tool meant to be invoked ad hoc via `docker compose run --rm`.
- **Determinism and testability.** The classifier is a plain function with no model
  weights to download, version, or mock — its unit tests exercise the exact same code
  path that runs in production.

**Acknowledged limitation, stated explicitly rather than hidden**: there is no measured
accuracy for this classifier against a human-labeled ground truth. The only validation
performed is a plausibility check — the resulting label distribution over the live data
(11,085 positive / 5,303 neutral / 1,172 negative out of ~17.5k reviews) matches the
visibly praise-heavy nature of the dataset rather than collapsing onto one label — plus
unit tests against hand-picked examples. It has known blind spots: unrecognized typos,
words outside its ~150-entry lexicon, sentiment that depends on context rather than word
choice, and profanity-based negativity (deliberately excluded from the checked-in
lexicon), which falls through to `neutral` instead of `negative`.

## Real bugs found during development

These are kept here deliberately, not smoothed over, because they're representative of
the actual engineering process on this project, not just a list of shipped features.

### Kafka advertised-listener bug (Day 6)

**Observed**: the first time two real services (not host-side test code) exchanged
Kafka traffic over the Docker Compose network, `playstore-scraper` and
`storage-consumer` could each complete an initial bootstrap connection to Kafka, but
neither could actually produce or consume messages against it.

**What this looked like at first / ruled out**: the symptom (connection succeeds, then
nothing happens) looked at first like a broker-readiness or client-library issue,
since the same code already worked fine in isolated host-side integration tests against
Kafka's host-mapped port.

**Root cause and fix**: `docker-compose.yml`'s `kafka` service advertised a single
listener, `localhost:9092`. That works for a host-side client, but breaks
container-to-container traffic: a container's initial bootstrap request to
`kafka:9092` succeeds, but Kafka's own metadata response then tells the client to
reconnect to `localhost:9092` for actual produce/consume traffic — which, resolved
*from inside another container*, points at that container itself, not the `kafka`
container. Fixed by splitting into two listeners: `PLAINTEXT` for container-to-container
traffic (advertised as `kafka:9092`, resolvable on the compose network) and
`PLAINTEXT_HOST` for host-side traffic (advertised as `localhost`, on the mapped host
port).

### Alembic version-table collision (Day 6)

**Observed**: `storage-consumer` needed its own Alembic setup for two new tables, in the
same `sahabino` Postgres database `app-list-api-fastapi` already used for the `apps`
table's own, separate Alembic history.

**What this would have caused**: Alembic tracks "what migration state is this database
at" in a single `alembic_version` table by default. Two independent migration
histories both defaulting to that same table name in the same database would each
overwrite the other's bookkeeping row, corrupting both services' idea of their own
current migration state.

**Fix**: gave `storage-consumer`'s `alembic/env.py` an explicit, distinct
`version_table` name (`alembic_version_storage_consumer`), leaving
`app-list-api-fastapi` on Alembic's default table name. `network-analyzer`, added
later, follows the same pattern with its own distinct version table.

### tshark version-drift bug affecting handshake RTT (Day 8)

**Observed**: `handshake_rtt_ms` (derived from tshark's `tcp.analysis.ack_rtt` field)
is sensitive to the exact `tshark` version. On a capture with many concurrent or
retried connections, tshark 4.4.16/4.4.18 leave `ack_rtt` uncomputed for a subset of
SYN-ACK packets that tshark 4.2.2 computes a value for — every other extracted metric
in the same table (packet counts, byte totals) agreed exactly across versions, only the
RTT calculation shifted.

**What this meant for the fix**: since every other metric matched, the discrepancy
wasn't a bug in `network-analyzer`'s own extraction logic (`pcap_metrics.py`) — it
traced to tshark's own internal completeness heuristic for that one derived field
changing between versions. The Debian-based `python:3.12-slim` image the other services
use doesn't offer a way around this either: Debian's stable releases jump from tshark
4.0.x (bookworm) straight to 4.4.x (trixie), with no 4.2.x available in either.

**Fix**: built `network-analyzer`'s Dockerfile on Ubuntu 24.04 instead, which ships
`tshark` 4.2.2 by default, and pinned the exact package version
(`4.2.2-1.1build3`) so a future base-image update can't silently drift the metric
again.

## Known limitations

Stated plainly, not hidden:

- **No FK-level referential integrity between services**, by design. `app_id` columns
  on `network_metrics`, `app_stats_snapshots`, and `reviews` are plain indexed
  integers, not foreign keys to `apps.id` — see Schema ownership above. Referential
  correctness is enforced at the application level, not the database level.
- **No measured sentiment-analysis accuracy.** The lexicon-based classifier's output
  has been checked for overall plausibility against the live data's label distribution
  and against hand-picked unit-test examples, but not against a human-labeled ground
  truth, so no precision/recall/accuracy figure exists for it.
- **`playstore-scraper` and `storage-consumer` intentionally have no Docker
  healthcheck**, unlike `app-list-api-fastapi`. This was a
  deliberate priority call, not an oversight: nothing else's `depends_on` needs either
  of these two services to be healthy before starting in a specific order, whereas the
  API service gates `playstore-scraper`'s own startup and previously caused a real
  race condition (see Day 4/Day 9 in `DAILY_LOG.md`) before it got a healthcheck.
- **The 9 apps whose package names were corrected late** (originally seeded with
  placeholder `com.placeholder.*` values, corrected across Days 2 and 4) have shorter
  historical data than the other 7 apps, since no real Play Store data could be scraped
  for them under a placeholder package name before the correction landed.
