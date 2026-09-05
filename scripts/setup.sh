#!/usr/bin/env bash
# One-time project setup: checks prerequisites, creates .env, installs git hooks.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Checking prerequisites..."

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
  echo "ERROR: docker compose (or docker-compose) is not installed." >&2
  exit 1
fi

echo "Docker and docker compose found."

if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "Creating .env from .env.example..."
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
else
  echo ".env already exists, leaving it untouched."
fi

echo "Installing git hooks..."
"$SCRIPT_DIR/install-git-hooks.sh"

echo "Setup complete."
