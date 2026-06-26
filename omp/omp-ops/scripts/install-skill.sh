#!/bin/bash
set -euo pipefail

# install-skill.sh
# Symlinks (or copies, if symlinking fails) the omp-ops skill from the
# jz-skills checkout into the local agent pool so OMP can discover it.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

TARGET_DIR="$HOME/.agents/pools/hermes-ops/omp-ops"

mkdir -p "$(dirname "$TARGET_DIR")"

# Remove any existing symlink/directory at the target.
if [[ -L "$TARGET_DIR" ]] || [[ -e "$TARGET_DIR" ]]; then
  rm -rf "$TARGET_DIR"
fi

# Prefer a symlink so future edits in the checkout are reflected immediately.
if ln -s "$SKILL_DIR" "$TARGET_DIR" 2>/dev/null; then
  METHOD="symlink"
elif cp -a "$SKILL_DIR" "$TARGET_DIR"; then
  METHOD="copy"
else
  jq -n \
    --arg target "$TARGET_DIR" \
    '{status:"error", message:("Failed to install skill to " + $target)}' >&2
  exit 1
fi

jq -n \
  --arg source "$SKILL_DIR" \
  --arg target "$TARGET_DIR" \
  --arg method "$METHOD" \
  '{status:"ok", source: $source, target: $target, method: $method}'
