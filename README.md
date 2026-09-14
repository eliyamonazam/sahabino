# Sahabino

A system for collecting and analyzing Google Play Store app data and network traffic
data: it tracks a curated list of apps, continuously scrapes their Play Store stats and
reviews, ingests manually captured pcap files into per-app network-quality metrics, and
runs a batch sentiment-analysis pass over collected reviews — with a Metabase dashboard
on top for analysis.

See [`docs/architecture.md`](docs/architecture.md) for the full design reasoning (schema
ownership, the message broker abstraction, why some services are batch tools, real bugs
found during development, and known limitations), and
[`docs/metabase-dashboard1.png`](docs/metabase-dashboard1.png) /
[`docs/metabase-dashboard2.png`](docs/metabase-dashboard2.png) for the analysis
dashboard built on top of the collected data.

## Services

| Service | Description |
|---|---|
| `app-list-api-fastapi` | FastAPI CRUD API for the tracked-apps list; owns the `apps` table's schema. Always-on. |
| `playstore-scraper` | Scrapes each tracked app's Play Store stats and reviews, publishes them to Kafka. Always-on. |
| `storage-consumer` | Consumes scraped stats/reviews from Kafka and persists them into Postgres. Always-on. |
| `network-analyzer` | Extracts network-quality metrics from manually captured pcap files into Postgres. Batch tool. |
| `sentiment-analyzer` | Classifies stored reviews as positive/neutral/negative. Batch tool. |

(`libs/message_broker` is a shared library used by `playstore-scraper` and
`storage-consumer`, not a deployed service; `postgres`, `kafka`, and `metabase` are
third-party infrastructure containers defined in `docker-compose.yml`.)

## Prerequisites

- Docker
- Docker Compose (v2, `docker compose`)

## Running the project

**Plain bash scripts:**

```bash
./scripts/setup.sh   # one-time setup: creates .env, installs git hooks
./scripts/run.sh      # starts the full stack
```

To stop everything:

```bash
./scripts/stop.sh
```

**Ansible playbook** (bonus feature — see below): does the same setup (installing
Docker if missing, creating `.env`, installing git hooks) plus bringing the stack up, as
one idempotent playbook run. Currently targets `localhost`; see `ansible/README.md` for
pointing it at a real remote host.

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml
```

Batch tools (`network-analyzer`, `sentiment-analyzer`) are not started by either of the
above — run them on demand:

```bash
docker compose run --rm network-analyzer
docker compose run --rm sentiment-analyzer
```

## Bonus features implemented

- **Swagger** — interactive API docs on `app-list-api-fastapi`: `/docs`.
- **Kafka** — the deployed stack's message broker for the Play Store pipeline, behind
  a shared `MessageBroker` abstraction that also has a working (tested, but currently
  unused in the deployed stack) Redis Streams implementation.
- **Ansible** — `ansible/playbook.yml` automates the same setup `scripts/setup.sh` +
  `scripts/run.sh` do, idempotently, including installing Docker itself on a bare
  Debian/Ubuntu target.
- **Sentiment analysis** — `sentiment-analyzer`, a lexicon-based Persian sentiment
  classifier that labels every stored review positive/neutral/negative.

## Linting and formatting

This repo uses [ruff](https://docs.astral.sh/ruff/) for Python linting and formatting, enforced automatically via [pre-commit](https://pre-commit.com/):

```bash
pip install pre-commit   # once, on your machine
pre-commit install       # once, per clone — activates the git hook
```

From then on, every `git commit` runs ruff (lint + format) against the files you're committing. If ruff has to fix something, that commit is blocked once so you can review the fixed files and re-stage them — this is normal `pre-commit` behavior, not a bug. Committing again after re-staging goes through.

To check the whole repo on demand (not just staged files):

```bash
pre-commit run --all-files
```

See `CONTRIBUTING.md` for the rest of the team's conventions.
