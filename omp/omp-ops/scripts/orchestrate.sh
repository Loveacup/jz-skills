#!/bin/bash
set -euo pipefail

# orchestrate.sh
# Entry orchestrator. Runs check-version.sh and executes the returned actions
# in order, using a file lock and a 5-minute sync cache.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
REFS_DIR="$SKILL_DIR/references"

LOCK_DIR="$SKILL_DIR/.orchestrate.lock"
CACHE_FILE="$HOME/.cache/omp-ops-last-sync"

mkdir -p "$HOME/.cache"
mkdir -p "$REFS_DIR"

# -----------------------------------------------------------------------------
# Locking (portable mkdir-based atomic lock; macOS lacks flock)
# -----------------------------------------------------------------------------

acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
    return 0
  fi
  echo '{"status":"locked","message":"Another sync is already running."}'
  return 1
}

acquire_lock || exit 0

# -----------------------------------------------------------------------------
# Check version / state
# -----------------------------------------------------------------------------

STATUS_JSON="$("$SCRIPT_DIR/check-version.sh")"

# Validate JSON.
if ! python3 -c 'import sys, json; json.load(sys.stdin)' <<<"$STATUS_JSON" >/dev/null 2>&1; then
  echo '{"status":"error","message":"check-version.sh returned invalid JSON"}' >&2
  echo "$STATUS_JSON" >&2
  exit 1
fi

# Extract the actions array.
ACTIONS="$(python3 -c 'import sys, json; d=json.load(sys.stdin); print("\n".join(d.get("actions", [])))' <<<"$STATUS_JSON")"

if [[ -z "$ACTIONS" ]]; then
  echo "$STATUS_JSON"
  exit 0
fi

# -----------------------------------------------------------------------------
# Execute actions in order
# -----------------------------------------------------------------------------

ACTION_ARRAY=()
while IFS= read -r line; do
  [[ -n "$line" ]] && ACTION_ARRAY+=("$line")
done <<<"$ACTIONS"

for action in "${ACTION_ARRAY[@]}"; do
  script_path="$SCRIPT_DIR/${action}.sh"
  if [[ ! -x "$script_path" ]]; then
    jq -n \
      --arg action "$action" \
      --arg script "$script_path" \
      '{status:"error", message:("Action script not found or not executable: " + $script + " (action: " + $action + ")")}' >&2
    exit 1
  fi

  if ! "$script_path"; then
    jq -n \
      --arg action "$action" \
      '{status:"error", message:("Action failed: " + $action)}' >&2
    exit 1
  fi
done

# -----------------------------------------------------------------------------
# Update cache and return
# -----------------------------------------------------------------------------

date +%s > "$CACHE_FILE"
echo "$STATUS_JSON"
