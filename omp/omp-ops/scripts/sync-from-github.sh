#!/bin/bash
set -euo pipefail

# sync-from-github.sh
# Pulls the latest omp-ops skill from Loveacup/jz-skills main branch into the
# local skill directory.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

GITHUB_REPO="Loveacup/jz-skills"
GITHUB_BRANCH="main"
GITHUB_SKILL_DIR="omp/omp-ops"

# Locate the root of the jz-skills checkout that contains this skill.
JZ_ROOT="$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$JZ_ROOT" ]]; then
  jq -n \
    --arg skill "$SKILL_DIR" \
    '{status:"error", message:("Skill directory is not inside a git repository: " + $skill)}' >&2
  exit 1
fi

# Make sure origin/main is up to date.
if ! git -C "$JZ_ROOT" fetch origin "$GITHUB_BRANCH" >/dev/null 2>&1; then
  jq -n \
    --arg repo "$GITHUB_REPO" \
    --arg branch "$GITHUB_BRANCH" \
    '{status:"error", message:("Failed to fetch origin/" + $branch + " from " + $repo)}' >&2
  exit 1
fi

# If the remote skill directory does not exist yet, there is nothing to pull.
if ! git -C "$JZ_ROOT" ls-tree "origin/$GITHUB_BRANCH" "$GITHUB_SKILL_DIR" >/dev/null 2>&1; then
  jq -n \
    --arg dir "$GITHUB_SKILL_DIR" \
    '{status:"no_remote", message:("Remote skill directory not yet present on origin/main: " + $dir)}'
  exit 0
fi

# Refuse to overwrite uncommitted local changes under the skill path.
if git -C "$JZ_ROOT" status --porcelain "$GITHUB_SKILL_DIR" | grep -q .; then
  jq -n \
    --arg dir "$GITHUB_SKILL_DIR" \
    '{status:"error", message:("Local skill directory has uncommitted changes; refusing to overwrite: " + $dir)}' >&2
  exit 1
fi

# Checkout the remote skill tree into the working copy.
if ! git -C "$JZ_ROOT" checkout "origin/$GITHUB_BRANCH" -- "$GITHUB_SKILL_DIR"; then
  jq -n \
    --arg dir "$GITHUB_SKILL_DIR" \
    '{status:"error", message:("Failed to checkout " + $dir + " from origin/main.")}' >&2
  exit 1
fi

jq -n \
  --arg dir "$GITHUB_SKILL_DIR" \
  --arg branch "$GITHUB_BRANCH" \
  '{status:"ok", message:("Pulled " + $dir + " from origin/" + $branch + ".")}'
