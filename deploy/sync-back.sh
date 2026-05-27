#!/bin/bash
# sync-back.sh — Reverse sync: Hermes → git repo (with auto-sanitize)
set -eu
set +H
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=false
SANITIZE=true

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --no-sanitize) SANITIZE=false ;;
  esac
done

echo "🔍 Reverse sync: Hermes → jz-skills repo"
[ "$DRY_RUN" = true ] && echo "   (DRY RUN — no files will be copied)"
[ "$SANITIZE" = false ] && echo "   ⚠️  SANITIZE OFF — sensitive data will NOT be stripped"
echo ""

sanitize_dir() {
  local dir="$1"
  find "$dir" -type f \( -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" \) | while read -r file; do
    local tmp
    tmp="$(mktemp)"
    cp "$file" "$tmp"
    awk -v home="$HOME/" '{gsub(home, "~/")}1' "$tmp" > "${tmp}.new" && mv "${tmp}.new" "$tmp"
    sed -i '' -E 's/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/<email redacted>/g' "$tmp" 2>/dev/null || \
    sed -i -E 's/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/<email redacted>/g' "$tmp"
    sed -i '' -E 's/(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9]+\.[0-9]+/<internal IP redacted>/g' "$tmp" 2>/dev/null || \
    sed -i -E 's/(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9]+\.[0-9]+/<internal IP redacted>/g' "$tmp"
    sed -i '' -E 's/\b(gho|sk|sk-ant|hf)_[a-zA-Z0-9_-]{25,}/<API key redacted>/g' "$tmp" 2>/dev/null || \
    sed -i -E 's/\b(gho|sk|sk-ant|hf)_[a-zA-Z0-9_-]{25,}/<API key redacted>/g' "$tmp"
    sed -i '' -E 's/\b[A-Z_]{3,}(KEY|TOKEN|SECRET)\s*=\s*["'"'"']?[a-zA-Z0-9_\.\-]{20,}["'"'"']?/<API key redacted>/g' "$tmp" 2>/dev/null || \
    sed -i -E 's/\b[A-Z_]{3,}(KEY|TOKEN|SECRET)\s*=\s*["'"'"']?[a-zA-Z0-9_\.\-]{20,}["'"'"']?/<API key redacted>/g' "$tmp"
    if ! cmp -s "$file" "$tmp"; then
      cp "$tmp" "$file"
      [ "$DRY_RUN" = false ] && echo "     🧹 sanitized: $(basename "$file")"
    fi
    rm -f "$tmp"
  done
}

HERMES_BASE="$HOME/.hermes/skills"
CHANGED=0

PAIRS=(
  # === shared ===
  "shared/grill-with-docs|governance/grill-with-docs"
  "shared/skill-authoring|governance/skill-authoring"
  "shared/pdf|productivity/pdf"
  "shared/strategic-insight-longform|productivity/strategic-insight-longform"
  "shared/voice-to-markdown-workflow|productivity/voice-to-markdown-workflow"

  # === hermes ===
  "hermes/web-research-router|research/web-research-router"
  "hermes/github-code-explorer|github/github-code-explorer"
  "hermes/tradingagents|research/tradingagents"
  "hermes/llm-wiki|research/llm-wiki"
  "hermes/arxiv|research/arxiv"
  "hermes/auto-diary|auto-diary"
  "hermes/bilibili-video-analyzer|bilibili-video-analyzer"
  "hermes/xhs-crawler|xhs-crawler"
  "hermes/calendar-manager|calendar-manager"
  "hermes/de-slop|de-slop"
  "hermes/claude-code|autonomous-ai-agents/claude-code"

  # === hermes-3S6M-profiles/common ===
  "hermes-3S6M-profiles/common/three-provinces-constitution|governance/three-provinces-constitution"
  "hermes-3S6M-profiles/common/financial-research-agents|research/financial-research-agents"

  # === hermes-3S6M-profiles/regent ===
  "hermes-3S6M-profiles/regent/kanban-orchestrator|profiles/regent/skills/kanban-orchestrator"
  "hermes-3S6M-profiles/regent/kanban-worker|profiles/regent/skills/kanban-worker"
  "hermes-3S6M-profiles/regent/kanban-gate|profiles/regent/skills/kanban-gate"
  "hermes-3S6M-profiles/regent/6m-smoke-test|profiles/regent/skills/6m-smoke-test"
  "hermes-3S6M-profiles/regent/morning-news-briefing|profiles/regent/skills/productivity/morning-news-briefing"
  "hermes-3S6M-profiles/regent/claude-code|profiles/regent/skills/autonomous-ai-agents/claude-code"

  # === profiles/gongbu ===
  "hermes-3S6M-profiles/gongbu/disk-cleanup|profiles/gongbu/skills/disk-cleanup"
  "hermes-3S6M-profiles/gongbu/infra-health-check|profiles/gongbu/skills/infra-health-check"
  "hermes-3S6M-profiles/gongbu/infra-monitoring|profiles/gongbu/skills/infra-monitoring"
  "hermes-3S6M-profiles/gongbu/surge-gateway|profiles/gongbu/skills/surge-gateway"
  "hermes-3S6M-profiles/gongbu/agent-observability|profiles/gongbu/skills/agent-observability"

  # === profiles/tester ===
  "hermes-3S6M-profiles/tester/code-review-toolkit|profiles/tester/skills/code-review-toolkit"
  "hermes-3S6M-profiles/tester/agent-security-audit|profiles/tester/skills/agent-security-audit"

  # === profiles/jiangzuojian ===
  "hermes-3S6M-profiles/jiangzuojian/delivery-gate|profiles/jiangzuojian/skills/delivery-gate"
  "hermes-3S6M-profiles/jiangzuojian/specialist-engineer|profiles/jiangzuojian/skills/specialist-engineer"

  # === profiles/protocol ===
  "hermes-3S6M-profiles/protocol/md-to-pdf|profiles/protocol/skills/md-to-pdf"

  # === profiles/auditor ===
  "hermes-3S6M-profiles/auditor/agent-audit-evaluation|profiles/auditor/skills/agent-audit-evaluation"

  # === profiles/archivist ===
  "hermes-3S6M-profiles/archivist/agent-memory-manager|profiles/archivist/skills/agent-memory-manager"

  # === profiles/shangshu ===
  "hermes-3S6M-profiles/shangshu/a2a-protocol|profiles/shangshu/skills/a2a-protocol"

  # === profiles/budget ===
  "hermes-3S6M-profiles/budget/agent-cost-manager|profiles/budget/skills/agent-cost-manager"

  # === profiles/registry ===
  "hermes-3S6M-profiles/registry/agent-registry|profiles/registry/skills/agent-registry"

  # === profiles/hanlinyuan ===
  "hermes-3S6M-profiles/hanlinyuan/deep-research-agent|profiles/hanlinyuan/skills/deep-research-agent"
)

for pair in "${PAIRS[@]}"; do
  repo_path="${pair%%|*}"
  herm_path="${pair##*|}"

  if [[ "$herm_path" == profiles/* ]]; then
    src="$HOME/.hermes/$herm_path"
  else
    src="$HERMES_BASE/$herm_path"
  fi
  dst="$REPO_ROOT/$repo_path"

  [ ! -d "$src" ] && { echo "  ⚠️  $repo_path → source not found — skipped"; continue; }
  [ ! -d "$dst" ] && { echo "  ⚠️  $repo_path → dest not found — skipped"; continue; }

  diff_output=$(diff -rq "$src" "$dst" 2>/dev/null) && continue
  echo "  📝 $repo_path"
  echo "$diff_output" | sed 's/^/     /'

  if [ "$DRY_RUN" = false ]; then
    rm -rf "$dst"
    cp -r "$src" "$dst"
    [ "$SANITIZE" = true ] && sanitize_dir "$dst"
    CHANGED=$((CHANGED + 1))
  fi
done

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "🏁 Dry run complete. Run without --dry-run to apply."
elif [ "$CHANGED" -eq 0 ]; then
  echo "✅ No changes — repo is up to date."
else
  echo "✅ $CHANGED skill(s) synced back."
  [ "$SANITIZE" = true ] && echo "   🧹 Auto-sanitized: home paths → ~/, emails → redacted, private IPs → redacted, API keys → redacted"
  echo ""
  echo "  cd $REPO_ROOT && git diff && git commit -am 'sync back' && git push"
fi
