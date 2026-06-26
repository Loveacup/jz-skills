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

VERSION="$(cat "$REFS_DIR/VERSION" 2>/dev/null | tr -d '[:space:]' || echo "0.0.0-0")"
[[ -n "$VERSION" ]] || VERSION="0.0.0-0"

JZ_ROOT="$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$JZ_ROOT" ]]; then
  jq -n \
    --arg skill "$SKILL_DIR" \
    '{status:"error", message:("Skill directory is not inside a git repository: " + $skill)}' >&2
  exit 1
fi

# Remove the dirty marker before staging so it is never committed.
rm -f "$SKILL_DIR/.dirty"

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

git -C "$JZ_ROOT" commit -m "sync: omp-ops $VERSION"

if ! git -C "$JZ_ROOT" push origin "$GITHUB_BRANCH"; then
  jq -n \
    --arg branch "$GITHUB_BRANCH" \
    '{status:"error", message:("Failed to push to origin/" + $branch + ".")}' >&2
  exit 1
fi

jq -n \
  --arg version "$VERSION" \
  '{status:"ok", message:("Pushed omp-ops " + $version + " to origin/main."), version: $version}'
