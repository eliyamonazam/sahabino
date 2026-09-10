#!/usr/bin/env bash
# Starts the full stack in the background: infrastructure (postgres, kafka,
# metabase), both app-list APIs, the scraper, and the storage consumer.
# network-analyzer also comes up as part of this (`up -d` starts every
# service in docker-compose.yml unless given specific service names), but
# since it's a one-shot batch tool with no restart policy, that just means
# one harmless analysis pass rather than a long-running process - see the
# comment on that service in docker-compose.yml and
# services/network-analyzer/README.md for its actual intended usage
# (`docker compose run --rm network-analyzer`).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

docker compose up -d
