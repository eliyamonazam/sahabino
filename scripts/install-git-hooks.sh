#!/usr/bin/env bash
# Installs local git hooks:
#   commit-msg  - strips tool-generated attribution lines from commit messages
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

mkdir -p "$HOOKS_DIR"

cat > "$HOOKS_DIR/commit-msg" <<'EOF'
#!/usr/bin/env bash
# Removes tool-generated attribution lines from the commit message before it is saved.
set -euo pipefail

MSG_FILE="$1"

sed -i \
  -e '/^Co-Authored-By: Claude/Id' \
  -e '/^Generated with \[Claude Code\]/Id' \
  -e '/^Claude-Session:/Id' \
  "$MSG_FILE"

exit 0
EOF

chmod +x "$HOOKS_DIR/commit-msg"

echo "Git hooks installed: commit-msg"
