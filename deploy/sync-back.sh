#!/bin/bash
# sync-back.sh — Reverse sync: Hermes → git repo (with auto-sanitize)
#
# Safe default: report-only. Applying changes requires `--apply` plus either
# one or more `--only <repo-path>` scopes, or an explicit `--force-all`.
set -eu
set +H
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=true
SANITIZE=true
FORCE_ALL=false
ONLY_PATHS=()

usage() {
  cat <<'EOF'
Usage:
  ./deploy/sync-back.sh [--dry-run] [--only <repo-path> ...]
  ./deploy/sync-back.sh --apply --only <repo-path> [--only <repo-path> ...]
  ./deploy/sync-back.sh --apply --force-all

Examples:
  ./deploy/sync-back.sh --dry-run
  ./deploy/sync-back.sh --only shared/obsidian --dry-run
  ./deploy/sync-back.sh --apply --only shared/obsidian

Notes:
  - Default is dry-run to avoid unrelated runtime drift polluting commits.
  - Use --only for scoped writeback. Full writeback requires --force-all.
EOF
}

while [ "$#" -gt 0 ]; do
  arg="$1"
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --apply) DRY_RUN=false ;;
    --force-all) FORCE_ALL=true ;;
    --only)
      shift
      [ "$#" -gt 0 ] || { echo "ERROR: --only requires a repo path" >&2; exit 2; }
      ONLY_PATHS+=("$1")
      ;;
    --only=*)
      ONLY_PATHS+=("${arg#--only=}")
      ;;
    --no-sanitize) SANITIZE=false ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$DRY_RUN" = false ] && [ "$FORCE_ALL" = false ] && [ "${#ONLY_PATHS[@]}" -eq 0 ]; then
  echo "ERROR: refusing full sync-back without scope." >&2
  echo "Use --apply --only <repo-path> for scoped writeback, or --apply --force-all after manual review." >&2
  exit 2
fi

echo "🔍 Reverse sync: Hermes → jz-skills repo"
[ "$DRY_RUN" = true ] && echo "   (DRY RUN — no files will be copied)"
[ "${#ONLY_PATHS[@]}" -gt 0 ] && printf '   scope: %s\n' "${ONLY_PATHS[@]}"
[ "$DRY_RUN" = false ] && [ "$FORCE_ALL" = true ] && echo "   ⚠️  FORCE ALL — applying every mapped drift"
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
DRIFT_COUNT=0
SCOPE_DRIFT_COUNT=0

in_scope() {
  local repo_path="$1"
  [ "${#ONLY_PATHS[@]}" -eq 0 ] && return 0
  local wanted
  for wanted in "${ONLY_PATHS[@]}"; do
    if [ "$repo_path" = "$wanted" ]; then
      return 0
    fi
  done
  return 1
}

PAIRS=(
  # === shared ===
  "shared/grill-with-docs|governance/grill-with-docs"
  "shared/skill-authoring|governance/skill-authoring"
  "shared/2pdf|productivity/pdf"
  "shared/strategic-insight-longform|productivity/strategic-insight-longform"
  "shared/voice-to-markdown-workflow|productivity/voice-to-markdown-workflow"
  "shared/bookmark-organizer|bookmark-organizer"
  "shared/github|github"
  "shared/xhs-tech-writer|hermes/xhs-tech-writer"

  # === hermes ===
  "hermes/cron-worker|cron-worker"
  "hermes/web-research-router|research/web-research-router"
  "hermes/source-verification|research/source-verification"
  "hermes/tradingagents|research/tradingagents"
  "hermes/arxiv|research/arxiv"
  "hermes/auto-diary|auto-diary"
  "shared/bilibili-video-analyzer|bilibili-video-analyzer"
  "hermes/xhs-crawler|xhs-crawler"
  "hermes/calendar-manager|calendar-manager"
  "hermes/de-slop|de-slop"
  "hermes/claude-code|autonomous-ai-agents/claude-code"
  "hermes/kanban-orchestrator|devops/kanban-orchestrator"
  "hermes/kanban-codex-lane|autonomous-ai-agents/kanban-codex-lane"
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
  DRIFT_COUNT=$((DRIFT_COUNT + 1))

  if ! in_scope "$repo_path"; then
    SCOPE_DRIFT_COUNT=$((SCOPE_DRIFT_COUNT + 1))
    echo "  ↪️  $repo_path (out of scope)"
    echo "$diff_output" | sed 's/^/     /'
    continue
  fi

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
  echo "🏁 Dry run complete."
  echo "   Apply with: ./deploy/sync-back.sh --apply --only <repo-path>"
elif [ "$CHANGED" -eq 0 ]; then
  echo "✅ No changes — repo is up to date."
else
  echo "✅ $CHANGED skill(s) synced back."
  [ "$SANITIZE" = true ] && echo "   🧹 Auto-sanitized: home paths → ~/, emails → redacted, private IPs → redacted, API keys → redacted"
  echo ""
  echo "  cd $REPO_ROOT && ./deploy/skill-drift-summary.sh && git diff"
fi

if [ "$SCOPE_DRIFT_COUNT" -gt 0 ]; then
  echo "⚠️  $SCOPE_DRIFT_COUNT drifted mapping(s) were outside the requested scope."
  echo "   Review them separately; do not batch them into the current commit."
elif [ "$DRIFT_COUNT" -gt 1 ] && [ "${#ONLY_PATHS[@]}" -eq 0 ] && [ "$DRY_RUN" = true ]; then
  echo "⚠️  Multiple drifted mappings detected. Use scoped --only writeback to avoid commit pollution."
fi
