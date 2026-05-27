#!/bin/bash
# sync-back.sh — Reverse sync: Hermes → git repo (with auto-sanitize)
set -eu
set +H                           # MUST be at top level — disables ! history expansion
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

# === Sanitize: strip sensitive patterns from text files ===
sanitize_dir() {
  local dir="$1"
  find "$dir" -type f \( -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" \) | while read -r file; do
    local tmp
    tmp="$(mktemp)"
    cp "$file" "$tmp"

    # 1. Home directory paths → ~/
    awk -v home="$HOME/" '{gsub(home, "~/")}1' "$tmp" > "${tmp}.new" && mv "${tmp}.new" "$tmp"

    # 2. Email addresses → <redacted>
    sed -i '' -E 's/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/<email redacted>/g' "$tmp" 2>/dev/null || \
    sed -i -E 's/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/<email redacted>/g' "$tmp"

    # 3. Private IPs → <redacted>
    sed -i '' -E 's/(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9]+\.[0-9]+/<internal IP redacted>/g' "$tmp" 2>/dev/null || \
    sed -i -E 's/(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9]+\.[0-9]+/<internal IP redacted>/g' "$tmp"

    # 4. API keys & tokens → <redacted>
    #    Matches: gho_xxx, sk-xxx, hf_xxx, and KEY/TOKEN/SECRET=value patterns
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
  "shared/web-research-router|research/web-research-router"
  "shared/github-code-explorer|github/github-code-explorer"
  "shared/grill-with-docs|governance/grill-with-docs"
  "shared/skill-authoring|governance/skill-authoring"
  "hermes/financial-research-agents|research/financial-research-agents"
  "hermes/tradingagents|research/tradingagents"
  "hermes/llm-wiki|research/llm-wiki"
  "hermes/arxiv|research/arxiv"
  "hermes/three-provinces-constitution|governance/three-provinces-constitution"
  "hermes/6m-smoke-test|governance/6m-smoke-test"
  "hermes/kanban-gate|devops/kanban-gate"
  "hermes/kanban-orchestrator|devops/kanban-orchestrator"
  "hermes/kanban-worker|devops/kanban-worker"
  "hermes/surge-gateway|devops/surge-gateway"
  "profiles/gongbu/disk-cleanup|profiles/gongbu/skills/disk-cleanup"
  "profiles/gongbu/infra-health-check|profiles/gongbu/skills/infra-health-check"
  "profiles/gongbu/infra-monitoring|profiles/gongbu/skills/infra-monitoring"
  "profiles/jiangzuojian/delivery-gate|profiles/jiangzuojian/skills/delivery-gate"
  "profiles/protocol/md-to-pdf|profiles/protocol/skills/md-to-pdf"
  "profiles/tester/code-review-toolkit|profiles/tester/skills/code-review-toolkit"
)

for pair in "${PAIRS[@]}"; do
  repo_path="${pair%%|*}"
  herm_path="${pair##*|}"
  
  # Profile skills live under ~/.hermes/profiles/, not ~/.hermes/skills/
  if [[ "$herm_path" == profiles/* ]]; then
    # Strip the leading "profiles/<name>/" part — the actual skill path should be
    # ~/.hermes/profiles/<name>/skills/<category>/<skill>
    # herm_path format: profiles/gongbu/skills/gongbu/disk-cleanup
    #           maps to: ~/.hermes/profiles/gongbu/skills/gongbu/disk-cleanup
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
