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

  # === hermes ===
  "hermes/web-research-router|research/web-research-router"
  "hermes/github-code-explorer|github/github-code-explorer"
  "hermes/financial-research-agents|research/financial-research-agents"
  "hermes/tradingagents|research/tradingagents"
  "hermes/llm-wiki|research/llm-wiki"
  "hermes/arxiv|research/arxiv"
  "hermes/three-provinces-constitution|governance/three-provinces-constitution"
  "hermes/strategic-insight-longform|imported-claude/strategic-insight-longform"
  "hermes/voice-to-markdown-workflow|imported-claude/voice-to-markdown-workflow"
  "hermes/auto-diary|auto-diary"
  "hermes/bilibili-video-analyzer|bilibili-video-analyzer"
  "hermes/xhs-crawler|xhs-crawler"

  # === profiles/regent ===
  "profiles/regent/kanban-orchestrator|profiles/regent/skills/kanban-orchestrator"
  "profiles/regent/kanban-worker|profiles/regent/skills/kanban-worker"
  "profiles/regent/kanban-gate|profiles/regent/skills/kanban-gate"
  "profiles/regent/6m-smoke-test|profiles/regent/skills/6m-smoke-test"
  "profiles/regent/morning-news-briefing|profiles/regent/skills/productivity/morning-news-briefing"

  # === profiles/gongbu ===
  "profiles/gongbu/disk-cleanup|profiles/gongbu/skills/disk-cleanup"
  "profiles/gongbu/infra-health-check|profiles/gongbu/skills/infra-health-check"
  "profiles/gongbu/infra-monitoring|profiles/gongbu/skills/infra-monitoring"
  "profiles/gongbu/surge-gateway|profiles/gongbu/skills/surge-gateway"
  "profiles/gongbu/agent-observability|profiles/gongbu/skills/agent-observability"

  # === profiles/tester ===
  "profiles/tester/code-review-toolkit|profiles/tester/skills/code-review-toolkit"
  "profiles/tester/agent-security-audit|profiles/tester/skills/agent-security-audit"

  # === profiles/jiangzuojian ===
  "profiles/jiangzuojian/delivery-gate|profiles/jiangzuojian/skills/delivery-gate"
  "profiles/jiangzuojian/specialist-engineer|profiles/jiangzuojian/skills/specialist-engineer"

  # === profiles/protocol ===
  "profiles/protocol/md-to-pdf|profiles/protocol/skills/md-to-pdf"

  # === profiles/auditor ===
  "profiles/auditor/agent-audit-evaluation|profiles/auditor/skills/agent-audit-evaluation"

  # === profiles/archivist ===
  "profiles/archivist/agent-memory-manager|profiles/archivist/skills/agent-memory-manager"

  # === profiles/shangshu ===
  "profiles/shangshu/a2a-protocol|profiles/shangshu/skills/a2a-protocol"

  # === profiles/budget ===
  "profiles/budget/agent-cost-manager|profiles/budget/skills/agent-cost-manager"

  # === profiles/registry ===
  "profiles/registry/agent-registry|profiles/registry/skills/agent-registry"

  # === profiles/hanlinyuan ===
  "profiles/hanlinyuan/deep-research-agent|profiles/hanlinyuan/skills/deep-research-agent"
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
