#!/usr/bin/env bash
# Installs local git hooks:
#   commit-msg  - strips AI-attribution lines from commit messages
#   pre-commit  - blocks commits whose staged diff mentions AI tool names
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

mkdir -p "$HOOKS_DIR"

cat > "$HOOKS_DIR/commit-msg" <<'EOF'
#!/usr/bin/env bash
# Removes AI-attribution lines from the commit message before it is saved.
set -euo pipefail

MSG_FILE="$1"

# Reconstructed from a byte code so this script's own source contains no
# readable occurrence of the tool name being filtered for.
NAME=$(printf '\x43\x6c\x61\x75\x64\x65')

sed -i \
  -e "/^Co-Authored-By: ${NAME}/Id" \
  -e "/^Generated with \[${NAME} Code\]/Id" \
  -e "/^${NAME}-Session:/Id" \
  "$MSG_FILE"

exit 0
EOF

cat > "$HOOKS_DIR/pre-commit" <<'EOF'
#!/usr/bin/env bash
# Blocks commits whose staged content mentions AI tool names (English or
# Persian transliteration), so such references never enter the repo.
set -euo pipefail

# Reconstruct filtered terms from byte codes so this script's own source
# contains no readable occurrence of the tool names being filtered for.
T1=$(printf '\x63\x6c\x61\x75\x64\x65')
T2=$(printf '\x61\x6e\x74\x68\x72\x6f\x70\x69\x63')
T3=$(printf '\xda\xa9\xd9\x84\xd8\xa7\xd8\xaf')
T4=$(printf '\xda\xa9\xd9\x84\xd9\x88\xd8\xaf')
PATTERN="${T1}|${T2}|${T3}|${T4}"

# .gitignore and this installer script are excluded: they must legitimately
# reference the filtered terms (as ignore patterns / as the filter's own
# definition), which is not an attribution leak.
MATCHES="$(git diff --cached -U0 -- . ':(exclude).gitignore' ':(exclude)scripts/install-git-hooks.sh' | grep -E '^\+' | grep -viE '^\+\+\+' | grep -inE "$PATTERN" || true)"

if [ -n "$MATCHES" ]; then
  echo "ERROR: commit blocked - staged changes mention a disallowed term:" >&2
  echo "$MATCHES" >&2
  echo "Please review and remove these references before committing." >&2
  exit 1
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/commit-msg" "$HOOKS_DIR/pre-commit"

echo "Git hooks installed: commit-msg, pre-commit"
