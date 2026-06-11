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
  "shared/github|github"
  "shared/xhs-tech-writer|hermes/xhs-tech-writer"

  # === hermes ===
  "hermes/cron-worker|cron-worker"
  "hermes/web-research-router|research/web-research-router"
  "hermes/source-verification|research/source-verification"
  "hermes/tradingagents|research/tradingagents"
  "hermes/arxiv|research/arxiv"
  "hermes/auto-diary|auto-diary"
  "hermes/bilibili-video-analyzer|bilibili-video-analyzer"
  "hermes/xhs-crawler|xhs-crawler"
  "hermes/calendar-manager|calendar-manager"
  "hermes/de-slop|de-slop"
  "hermes/claude-code|autonomous-ai-agents/claude-code"
  "hermes/cccmux|hermes/cccmux"
  "hermes/cqi-plan-writer|governance/cqi-plan-writer"
  "hermes/supermemory-hermes|governance/supermemory-hermes"
  "hermes/memory-hub|governance/memory-hub"
  "hermes/mac-doctor|apple/mac-doctor"
  "hermes/tts-manager|hermes/tts-manager"
  "hermes/tech-support-email|hermes/tech-support-email"
  "hermes/news-assembly|productivity/news-assembly"

  "hermes/morning-news-briefing|productivity/morning-news-briefing"
  "hermes/telegram-topic-manager|social-media/telegram-topic-manager"
  "hermes/dingtalk-message-monitor|social-media/dingtalk-message-monitor"
  "hermes/surge-gateway|devops/surge-gateway"
  "hermes/openwrt-router|smart-home/openwrt-router"
  "hermes/unifi-ops|smart-home/unifi-ops"
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
    # Clean dev artifacts that shouldn't be in the repo
    find "$dst" -name '.venv' -maxdepth 3 -type d -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -name '__pycache__' -maxdepth 3 -type d -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -name '*.pyc' -maxdepth 3 -type f -delete 2>/dev/null || true
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
