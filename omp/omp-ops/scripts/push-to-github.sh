#!/bin/bash
set -euo pipefail

# push-to-github.sh
# Syncs local omp-ops skill files to the jz-skills checkout, commits with a
# versioned message, and pushes to main.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
REFS_DIR="$SKILL_DIR/references"

GITHUB_BRANCH="main"
GITHUB_SKILL_DIR="omp/omp-ops"
DIRTY_MARKER="$SKILL_DIR/.dirty"

VERSION="$(cat "$REFS_DIR/VERSION" 2>/dev/null | tr -d '[:space:]' || echo "0.0.0-0")"
[[ -n "$VERSION" ]] || VERSION="0.0.0-0"

JZ_ROOT="$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$JZ_ROOT" ]]; then
  jq -n \
    --arg skill "$SKILL_DIR" \
    '{status:"error", message:("Skill directory is not inside a git repository: " + $skill)}' >&2
  exit 1
fi

# Helpers to keep the dirty marker in sync with the actual push outcome.
mark_dirty() { touch "$DIRTY_MARKER"; }
unmark_dirty() { rm -f "$DIRTY_MARKER"; }

# Remove the dirty marker before staging so it is never committed.
unmark_dirty

# If commit/push fails later, restore the marker so the next check-version run
# will retry.
restore_dirty_on_error() {
  jq -n \
    --arg version "$VERSION" \
    '{status:"error", message:("Failed to push omp-ops " + $version + ". Dirty marker restored.")}' >&2
  mark_dirty
  exit 1
}

# If there is nothing to commit under this skill path, we are done.
if ! git -C "$JZ_ROOT" status --porcelain "$GITHUB_SKILL_DIR" | grep -q .; then
  jq -n \
    --arg version "$VERSION" \
    '{status:"no_changes", message:("No changes to commit for omp-ops " + $version + ".")}'
  exit 0
fi

# Stage only the skill directory. New files are included; the dirty marker is not.
git -C "$JZ_ROOT" add "$GITHUB_SKILL_DIR"

if git -C "$JZ_ROOT" diff --cached --quiet; then
  jq -n \
    --arg version "$VERSION" \
    '{status:"no_changes", message:("Nothing staged for omp-ops " + $version + ".")}'
  exit 0
fi

if ! git -C "$JZ_ROOT" commit -m "sync: omp-ops $VERSION"; then
  restore_dirty_on_error
fi

if ! git -C "$JZ_ROOT" push origin "$GITHUB_BRANCH"; then
  restore_dirty_on_error
fi

jq -n \
  --arg version "$VERSION" \
  '{status:"ok", message:("Pushed omp-ops " + $version + " to origin/main."), version: $version}'
