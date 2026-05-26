#!/bin/bash
# sync-back.sh — Reverse sync: Hermes → git repo
# Copies changes from ~/.hermes/skills/ back to the repo for custom skills.
# Usage: ./deploy/sync-back.sh [--dry-run]

set -eu
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

echo "🔍 Reverse sync: Hermes → jz-skills repo"
[ "$DRY_RUN" = true ] && echo "   (DRY RUN — no files will be copied)"
echo ""

HERMES_BASE="$HOME/.hermes/skills"
CHANGED=0

# Each pair: "repo_path|hermes_relative_path"
PAIRS=(
  "shared/web-research-router|research/web-research-router"
  "shared/github-code-explorer|github/github-code-explorer"
  "shared/grill-with-docs|governance/grill-with-docs"
  "shared/skill-authoring|governance/skill-authoring"
  "hermes/financial-research-agents|research/financial-research-agents"
  "hermes/tradingagents|research/tradingagents"
  "hermes/llm-wiki|research/llm-wiki"
  "hermes/arxiv|research/arxiv"
)

for pair in "${PAIRS[@]}"; do
  repo_path="${pair%%|*}"
  herm_path="${pair##*|}"
  src="$HERMES_BASE/$herm_path"
  dst="$REPO_ROOT/$repo_path"

  if [ ! -d "$src" ]; then
    echo "  ⚠️  $repo_path → source not found — skipped"
    continue
  fi
  if [ ! -d "$dst" ]; then
    echo "  ⚠️  $repo_path → dest not found — skipped"
    continue
  fi

  diff_output=$(diff -rq "$src" "$dst" 2>/dev/null) && continue
  echo "  📝 $repo_path"
  echo "$diff_output" | sed 's/^/     /'

  if [ "$DRY_RUN" = false ]; then
    rm -rf "$dst"
    cp -r "$src" "$dst"
    CHANGED=$((CHANGED + 1))
  fi
done

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "🏁 Dry run complete. Run without --dry-run to apply."
elif [ "$CHANGED" -eq 0 ]; then
  echo "✅ No changes — repo is up to date."
else
  echo "✅ $CHANGED skill(s) synced back. Next:"
  echo "  cd $REPO_ROOT && git diff && git commit -am 'sync back' && git push"
fi
