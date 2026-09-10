#!/usr/bin/env bash
# Stops and removes all of the stack's containers (does not touch named
# volumes, so postgres/kafka data survives - use `docker compose down -v`
# manually if wiping that data is actually intended).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

docker compose down
