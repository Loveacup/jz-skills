#!/bin/bash
set -euo pipefail

# check-version.sh
# Detects version alignment across local OMP, local skill, GitHub skill, and official OMP.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
REFS_DIR="$SKILL_DIR/references"

GITHUB_REPO="Loveacup/jz-skills"
GITHUB_BRANCH="main"
GITHUB_SKILL_DIR="omp/omp-ops"
OFFICIAL_REPO="can1357/oh-my-pi"
OFFICIAL_BRANCH="main"

CACHE_FILE="$HOME/.cache/omp-ops-last-sync"
CACHE_TTL_SECONDS=300

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

version_base() {
  local v="$1"
  if [[ "$v" =~ -[0-9]+$ ]]; then
    echo "${v%-*}"
  else
    echo "$v"
  fi
}

version_revision() {
  local v="$1"
  if [[ "$v" =~ -([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo "0"
  fi
}

# Compare two semver-ish strings. Returns 0 if $1 > $2.
version_gt() {
  local a="$1" b="$2"
  [[ -n "$a" && -n "$b" && "$a" != "unknown" && "$b" != "unknown" ]] || return 1
  local max
  max="$(printf '%s\n%s\n' "$a" "$b" | sort -V | tail -n 1)"
  [[ "$max" == "$a" && "$a" != "$b" ]]
}

version_lt() {
  local a="$1" b="$2"
  [[ -n "$a" && -n "$b" && "$a" != "unknown" && "$b" != "unknown" ]] || return 1
  local max
  max="$(printf '%s\n%s\n' "$a" "$b" | sort -V | tail -n 1)"
  [[ "$max" == "$b" && "$a" != "$b" ]]
}

add_action() {
  local a="$1" existing
  if [[ ${#ACTIONS[@]} -gt 0 ]]; then
    for existing in "${ACTIONS[@]}"; do
      [[ "$existing" == "$a" ]] && return 0
    done
  fi
  ACTIONS+=("$a")
}

# -----------------------------------------------------------------------------
# Read versions
# -----------------------------------------------------------------------------

LOCAL_SKILL_VERSION="$(cat "$REFS_DIR/VERSION" 2>/dev/null | tr -d '[:space:]' || echo "0.0.0-0")"
[[ -n "$LOCAL_SKILL_VERSION" ]] || LOCAL_SKILL_VERSION="0.0.0-0"

LOCAL_OMP_VERSION="$(omp --version 2>/dev/null | sed -E 's#^(omp/|omp v|v)##; s#[[:space:]]##g' || echo "unknown")"
[[ -n "$LOCAL_OMP_VERSION" ]] || LOCAL_OMP_VERSION="unknown"

GITHUB_SKILL_VERSION="$(curl -fsSL "https://raw.githubusercontent.com/$GITHUB_REPO/$GITHUB_BRANCH/$GITHUB_SKILL_DIR/references/VERSION" 2>/dev/null | tr -d '[:space:]' || echo "0.0.0-0")"
[[ -n "$GITHUB_SKILL_VERSION" ]] || GITHUB_SKILL_VERSION="0.0.0-0"

OFFICIAL_OMP_VERSION="$(curl -fsSL "https://raw.githubusercontent.com/$OFFICIAL_REPO/$OFFICIAL_BRANCH/packages/coding-agent/package.json" 2>/dev/null | python3 -c 'import sys, json; print(json.load(sys.stdin).get("version", "unknown"))' || echo "unknown")"
[[ -n "$OFFICIAL_OMP_VERSION" ]] || OFFICIAL_OMP_VERSION="unknown"

# Treat non-semver strings (e.g. raw 404 bodies) as unknown/fallback.
SEMVER_RE='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9]+)?$'
[[ "$GITHUB_SKILL_VERSION" =~ $SEMVER_RE ]] || GITHUB_SKILL_VERSION="0.0.0-0"
[[ "$LOCAL_SKILL_VERSION" =~ $SEMVER_RE ]] || LOCAL_SKILL_VERSION="0.0.0-0"
[[ "$OFFICIAL_OMP_VERSION" =~ $SEMVER_RE ]] || OFFICIAL_OMP_VERSION="unknown"

# -----------------------------------------------------------------------------
# Determine actions
# -----------------------------------------------------------------------------

LOCAL_SKILL_BASE="$(version_base "$LOCAL_SKILL_VERSION")"
GITHUB_SKILL_BASE="$(version_base "$GITHUB_SKILL_VERSION")"
LOCAL_SKILL_REV="$(version_revision "$LOCAL_SKILL_VERSION")"
GITHUB_SKILL_REV="$(version_revision "$GITHUB_SKILL_VERSION")"

STATUS="synced"
MESSAGE="All aligned."
ACTIONS=()

# 1. Official OMP newer than GitHub skill base -> sync from official
if [[ "$OFFICIAL_OMP_VERSION" != "unknown" ]] && version_gt "$OFFICIAL_OMP_VERSION" "$GITHUB_SKILL_BASE"; then
  STATUS="sync-official"
  add_action "sync-from-official"
  add_action "push-to-github"
  add_action "sync-from-github"
  MESSAGE="Official OMP ($OFFICIAL_OMP_VERSION) is newer than jz-skills skill ($GITHUB_SKILL_VERSION). Syncing from official."
# 2. GitHub skill base newer than local skill base -> pull from GitHub
elif version_gt "$GITHUB_SKILL_BASE" "$LOCAL_SKILL_BASE"; then
  STATUS="sync-github"
  add_action "sync-from-github"
  MESSAGE="jz-skills skill ($GITHUB_SKILL_VERSION) is newer than local ($LOCAL_SKILL_VERSION). Pulling from GitHub."
# 3. Same base, different revision
elif [[ "$GITHUB_SKILL_BASE" == "$LOCAL_SKILL_BASE" ]]; then
  if [[ "$GITHUB_SKILL_REV" -gt "$LOCAL_SKILL_REV" ]]; then
    STATUS="sync-github"
    add_action "sync-from-github"
    MESSAGE="jz-skills skill revision ($GITHUB_SKILL_VERSION) is newer than local ($LOCAL_SKILL_VERSION). Pulling from GitHub."
  elif [[ "$LOCAL_SKILL_REV" -gt "$GITHUB_SKILL_REV" ]]; then
    STATUS="push-github"
    add_action "push-to-github"
    MESSAGE="Local skill revision ($LOCAL_SKILL_VERSION) is newer than jz-skills ($GITHUB_SKILL_VERSION). Pushing to GitHub."
  fi
# 4. Local skill base newer than GitHub skill base -> push to GitHub
elif version_gt "$LOCAL_SKILL_BASE" "$GITHUB_SKILL_BASE"; then
  STATUS="push-github"
  add_action "push-to-github"
  MESSAGE="Local skill ($LOCAL_SKILL_VERSION) is newer than jz-skills ($GITHUB_SKILL_VERSION). Pushing to GitHub."
fi

# 5. Check if local is dirty (uncommitted local changes)
LOCAL_DIRTY="false"
if [[ -f "$SKILL_DIR/.dirty" ]]; then
  LOCAL_DIRTY="true"
  if [[ "$STATUS" == "synced" ]]; then
    STATUS="push-github"
    add_action "push-to-github"
    MESSAGE="Local skill has uncommitted changes. Pushing to GitHub."
  fi
fi

# 6. Check cache: skip sync if recently synced
RECENT_SYNC="false"
if [[ -f "$CACHE_FILE" ]]; then
  LAST_SYNC="$(cat "$CACHE_FILE" 2>/dev/null || echo "0")"
  [[ "$LAST_SYNC" =~ ^[0-9]+$ ]] || LAST_SYNC="0"
  NOW="$(date +%s)"
  AGE=$((NOW - LAST_SYNC))
  if [[ "$AGE" -lt "$CACHE_TTL_SECONDS" ]]; then
    RECENT_SYNC="true"
    if [[ "$STATUS" != "synced" ]]; then
      STATUS="synced"
      ACTIONS=()
      MESSAGE="Sync skipped: synced ${AGE}s ago (cache TTL ${CACHE_TTL_SECONDS}s)."
    fi
  fi
fi

# -----------------------------------------------------------------------------
# Output JSON (python3 for guaranteed valid JSON)
# -----------------------------------------------------------------------------

export _CV_LOCAL_OMP="$LOCAL_OMP_VERSION"
export _CV_LOCAL_SKILL="$LOCAL_SKILL_VERSION"
export _CV_GITHUB_SKILL="$GITHUB_SKILL_VERSION"
export _CV_OFFICIAL_OMP="$OFFICIAL_OMP_VERSION"
export _CV_STATUS="$STATUS"
export _CV_MESSAGE="$MESSAGE"
export _CV_LOCAL_DIRTY="$LOCAL_DIRTY"
export _CV_RECENT_SYNC="$RECENT_SYNC"

# Newline-separated actions list for python3 to split.
_CV_ACTIONS=""
if [[ ${#ACTIONS[@]} -gt 0 ]]; then
  for a in "${ACTIONS[@]}"; do
    _CV_ACTIONS+="$a"$'\n'
  done
fi
export _CV_ACTIONS

python3 - <<'PY'
import json, os

actions = [a for a in os.environ.get("_CV_ACTIONS", "").splitlines() if a]

data = {
    "local_omp": os.environ.get("_CV_LOCAL_OMP", "unknown"),
    "local_skill": os.environ.get("_CV_LOCAL_SKILL", "0.0.0-0"),
    "github_skill": os.environ.get("_CV_GITHUB_SKILL", "0.0.0-0"),
    "official_omp": os.environ.get("_CV_OFFICIAL_OMP", "unknown"),
    "status": os.environ.get("_CV_STATUS", "synced"),
    "actions": actions,
    "local_dirty": os.environ.get("_CV_LOCAL_DIRTY", "false") == "true",
    "recent_sync": os.environ.get("_CV_RECENT_SYNC", "false") == "true",
    "message": os.environ.get("_CV_MESSAGE", ""),
}
print(json.dumps(data, indent=2))
PY
