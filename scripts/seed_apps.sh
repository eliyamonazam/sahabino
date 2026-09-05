#!/usr/bin/env bash
# Seeds the initial list of tracked apps via the running app-list-api-fastapi service.
#
# Package names marked with a placeholder comment are NOT real Google Play
# package ids — they need to be looked up and corrected before Day 4 (real
# scraping) starts. See the README / DAILY_LOG for the full placeholder list.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

HOST="${APP_LIST_API_FASTAPI_HOST:-localhost}"
PORT="${APP_LIST_API_FASTAPI_PORT:-8001}"
BASE_URL="http://${HOST}:${PORT}"

create_app() {
  local package_name="$1"
  local name="$2"
  local category="$3"

  echo "Creating: ${name} (${package_name}, ${category})"
  http_code=$(curl -s -o /tmp/seed_apps_response.json -w "%{http_code}" \
    -X POST "${BASE_URL}/apps" \
    -H "Content-Type: application/json" \
    -d "{\"package_name\": \"${package_name}\", \"name\": \"${name}\", \"category\": \"${category}\"}")

  if [ "$http_code" = "201" ]; then
    echo "  created."
  elif [ "$http_code" = "409" ]; then
    echo "  already exists, skipping."
  else
    echo "  unexpected status ${http_code}:"
    cat /tmp/seed_apps_response.json
  fi
}

# messenger
create_app "org.telegram.messenger" "Telegram" "messenger"
create_app "com.whatsapp" "Whatsapp" "messenger"

# operator (placeholder package names — see README/DAILY_LOG)
create_app "com.placeholder.myirancell" "Myirancell" "operator"
create_app "com.placeholder.mymci" "Mymci" "operator"
create_app "com.placeholder.myrightel" "MyRightel" "operator"

# video (placeholder package names — see README/DAILY_LOG)
create_app "com.placeholder.namava" "Namava" "video"
create_app "com.placeholder.lenz" "Lenz" "video"
create_app "com.placeholder.tamashakhonehtv" "Tamashakhonehtv" "video"

# word_game (placeholder package names — see README/DAILY_LOG)
create_app "com.placeholder.fandogh" "Fandogh" "word_game"
create_app "com.placeholder.amirza" "Amirza" "word_game"
create_app "com.placeholder.samavar" "Samavar" "word_game"

# chat_dating
create_app "ir.android.baham" "Baham" "chat_dating"
create_app "app.pinno" "Pinno" "chat_dating"

# social
create_app "com.instagram.android" "Instagram" "social"
create_app "com.facebook.katana" "Facebook" "social"
create_app "com.zhiliaoapp.musically" "Tiktok" "social"

echo "Done. GET ${BASE_URL}/apps to verify."
