#!/bin/bash
# skill-drift-summary.sh — lightweight pre-commit summary for skill changes.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

BASE="${1:-HEAD}"

changed_files="$(
  git status --porcelain=v1 |
    awk '
      {
        status=substr($0, 1, 2)
        path=substr($0, 4)
        if (path ~ / -> /) {
          split(path, parts, " -> ")
          path=parts[2]
        }
        print status "\t" path
      }
    '
)"
changed_files="$(printf '%s\n' "$changed_files" | sed '/^[[:space:]]*$/d' | sort -u)"

if [ -z "$changed_files" ]; then
  echo "skill drift summary: clean"
  exit 0
fi

skill_paths="$(
  printf '%s\n' "$changed_files" |
    awk '
      {
        status=$1
        path=$2
        if (status ~ /^R/ || status ~ /^C/) path=$3
        split(path, parts, "/")
        if (parts[1] == "shared" || parts[1] == "hermes" || parts[1] == "pi" || parts[1] == "cc") {
          if (parts[2] != "") print parts[1] "/" parts[2]
        }
      }
    ' | sort -u
)"

skill_count="$(printf '%s\n' "$skill_paths" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')"

critical_deletions="$(
  printf '%s\n' "$changed_files" |
    awk '$1 ~ /^D/ {print $2}' |
    grep -E '(^|/)(SKILL\.md|scripts/|references/|tests/)' || true
)"

sensitive_hits="$(
  git diff "$BASE" -- . ':!*.png' ':!*.jpg' ':!*.jpeg' ':!*.gif' ':!*.pdf' |
    grep -E '^\+.*((192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9]+\.[0-9]+|/Users/[A-Za-z0-9._-]+/|[A-Z_]{3,}(KEY|TOKEN|SECRET)[[:space:]]*=|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(gho|sk|sk-ant|hf)_[A-Za-z0-9_-]{25,})' || true
)"

echo "skill drift summary"
echo "base: $BASE"
echo ""
echo "changed paths:"
printf '%s\n' "$changed_files" | sed 's/^/  /'

if [ -n "$skill_paths" ]; then
  echo ""
  echo "affected skills ($skill_count):"
  printf '%s\n' "$skill_paths" | sed 's/^/  /'
fi

status="PASS"

if [ "$skill_count" -gt 1 ]; then
  status="WARN"
  echo ""
  echo "WARN: multiple skills changed; confirm this is intentional before commit/push."
fi

if [ -n "$critical_deletions" ]; then
  status="BLOCK"
  echo ""
  echo "BLOCK: critical skill files were deleted:"
  printf '%s\n' "$critical_deletions" | sed 's/^/  /'
fi

if [ -n "$sensitive_hits" ]; then
  status="BLOCK"
  echo ""
  echo "BLOCK: possible sensitive additions detected:"
  printf '%s\n' "$sensitive_hits" | sed 's/^/  /'
fi

echo ""
echo "status: $status"

case "$status" in
  PASS) exit 0 ;;
  WARN) exit 1 ;;
  BLOCK) exit 2 ;;
esac
