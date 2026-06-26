#!/bin/bash
set -euo pipefail

# sync-from-official.sh
# Fetches the latest official OMP version and documentation, updates the local
# skill reference files, records state, and marks the skill dirty.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
REFS_DIR="$SKILL_DIR/references"
OFFICIAL_DIR="$REFS_DIR/official"

OFFICIAL_REPO="can1357/oh-my-pi"
OFFICIAL_BRANCH="main"
VERSION_URL="https://raw.githubusercontent.com/$OFFICIAL_REPO/$OFFICIAL_BRANCH/packages/coding-agent/package.json"

mkdir -p "$OFFICIAL_DIR"

# -----------------------------------------------------------------------------
# Fetch official version
# -----------------------------------------------------------------------------

OFFICIAL_VERSION="$(curl -fsSL "$VERSION_URL" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("version", "unknown"))')"

if [[ -z "$OFFICIAL_VERSION" || "$OFFICIAL_VERSION" == "unknown" ]]; then
  jq -n \
    --arg url "$VERSION_URL" \
    '{status:"error", message:("Failed to fetch official OMP version from " + $url)}' >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Update local VERSION
# -----------------------------------------------------------------------------

echo "${OFFICIAL_VERSION}-0" > "$REFS_DIR/VERSION"

# -----------------------------------------------------------------------------
# Download docs
# -----------------------------------------------------------------------------

DOCS=(
  environment-variables.md
  providers.md
  skills.md
  custom-tools.md
  mcp-config.md
)

for doc in "${DOCS[@]}"; do
  curl -fsSL "https://raw.githubusercontent.com/$OFFICIAL_REPO/$OFFICIAL_BRANCH/docs/$doc" \
    -o "$OFFICIAL_DIR/$doc"
done

# First 500 lines of the coding-agent CHANGELOG.
# `head` closes the pipe early, which can cause curl to exit 56 (SIGPIPE).
# We tolerate a non-zero curl exit as long as the file was written.
set +e
curl -fsSL "https://raw.githubusercontent.com/$OFFICIAL_REPO/$OFFICIAL_BRANCH/packages/coding-agent/CHANGELOG.md" 2>/dev/null \
  | head -n 500 > "$OFFICIAL_DIR/CHANGELOG.md"
_curl_exit=${PIPESTATUS[0]}
set -e

if [[ $_curl_exit -ne 0 && ! -s "$OFFICIAL_DIR/CHANGELOG.md" ]]; then
  jq -n \
    --arg url "https://raw.githubusercontent.com/$OFFICIAL_REPO/$OFFICIAL_BRANCH/packages/coding-agent/CHANGELOG.md" \
    '{status:"error", message:("Failed to download CHANGELOG from " + $url)}' >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Update sync state
# -----------------------------------------------------------------------------

python3 - "$OFFICIAL_VERSION" "$REFS_DIR/sync-state.json" "$OFFICIAL_REPO" "$OFFICIAL_BRANCH" <<'PY'
import sys, json, datetime

version, path, repo, branch = sys.argv[1:5]
state = {}
try:
    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)
except Exception:
    pass

state.update({
    "official_omp": version,
    "synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "source": f"{repo} {branch}",
})

with open(path, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)
    f.write("\n")
PY

# -----------------------------------------------------------------------------
# Mark dirty
# -----------------------------------------------------------------------------

touch "$SKILL_DIR/.dirty"

jq -n \
  --arg version "$OFFICIAL_VERSION" \
  '{status:"ok", official_omp: $version, message:"Synced from official OMP."}'
