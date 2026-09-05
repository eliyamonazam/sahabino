# Sahabino

A system for collecting and analyzing Google Play Store app data and network traffic data.

## Prerequisites

- Docker
- Docker Compose (v2, `docker compose`)

## Running the project

```bash
./scripts/setup.sh   # one-time setup: creates .env, installs git hooks
./scripts/run.sh      # starts all infrastructure services
```

To stop everything:

```bash
./scripts/stop.sh
```

<!-- TODO: architecture overview, service descriptions, and development workflow to be added on later days. -->
