# Sahabino

A system for collecting and analyzing Google Play Store app data and network traffic data.

## Prerequisites

- Docker
- Docker Compose (v2, `docker compose`)

## Running the project

```bash
./scripts/setup.sh   # one-time setup: creates .env, installs git hooks
./scripts/run.sh      # starts the full stack
```

To stop everything:

```bash
./scripts/stop.sh
```

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

<!-- TODO: architecture overview, service descriptions, and development workflow to be added on later days. -->
