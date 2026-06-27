#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# incremental-cache.sh — 早新闻搜索增量缓存
# 用法:
#   ./incremental-cache.sh save 20260527    # 保存今日搜索为缓存
#   ./incremental-cache.sh diff 20260527    # 对比今日 vs 昨日
#   ./incremental-cache.sh clean 30         # 清理 30 天前缓存
# ═══════════════════════════════════════════════════════════

set -euo pipefail

ACTION="${1:-}"
DATE="${2:-$(date +%Y%m%d)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_BASE="${MORNING_NEWS_WORKSPACE:-/workspaces}"

# ── Help ──
if [ "$ACTION" = "-h" ] || [ "$ACTION" = "--help" ]; then
    echo "Usage: $0 {save|diff|clean} [YYYYMMDD|keep_days]"
    echo ""
    echo "  save 20260527    Save today's search results as cache"
    echo "  diff 20260527    Compare today vs yesterday's cached results"
    echo "  clean 30         Remove caches older than N days"
    exit 0
fi

# ── Compute yesterday ──
if [[ "$OSTYPE" == "darwin"* ]]; then
    YESTERDAY=$(date -j -v-1d -f "%Y%m%d" "$DATE" +%Y%m%d 2>/dev/null || echo "")
else
    YESTERDAY=$(date -d "$DATE -1 day" +%Y%m%d 2>/dev/null || echo "")
fi

SEARCH_DIR="$WORKSPACE_BASE/morning-news-$DATE/search"
CACHE_DIR="$SKILL_DIR/cache"

mkdir -p "$CACHE_DIR"

# ═══════════════════════════════════════════════════
# save — persist today's search artifacts as cache
# ═══════════════════════════════════════════════════
save_cache() {
    local cache_date="$CACHE_DIR/$DATE"
    mkdir -p "$cache_date"

    echo "💾 Saving search cache for $DATE → $cache_date"

    for lane in zh en market; do
        local src="$SEARCH_DIR/lane-$lane.json"
        local dst="$cache_date/lane-$lane.json"
        if [ -f "$src" ]; then
            cp "$src" "$dst"
            local articles=$(python3 -c "import json; d=json.load(open('$src')); print(len(d.get('articles',[])))" 2>/dev/null || echo "?")
            echo "   lane-$lane: $articles articles"
        else
            echo "   lane-$lane: MISSING (skipped)"
        fi
    done

    # Save manifest
    cat > "$cache_date/manifest.json" <<EOF
{
  "date": "$DATE",
  "saved_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "lanes_saved": $(ls "$cache_date"/lane-*.json 2>/dev/null | wc -l | tr -d ' ')
}
EOF
    echo "   manifest: written"
    echo "✓ Cache saved for $DATE"
}

# ═══════════════════════════════════════════════════
# diff — compare today's search vs yesterday's cache
# ═══════════════════════════════════════════════════
diff_cache() {
    local yesterday_cache="$CACHE_DIR/$YESTERDAY"

    echo "🔍 Diff: $DATE vs cached $YESTERDAY"
    echo ""

    if [ ! -d "$yesterday_cache" ]; then
        echo "⚠️  No cache for $YESTERDAY — full search required"
        echo '{"status":"no_cache","new_articles":null,"full_search":true}'
        return 0
    fi

    local new_count=0
    local total_count=0

    for lane in zh en market; do
        local today="$SEARCH_DIR/lane-$lane.json"
        local yesterday="$yesterday_cache/lane-$lane.json"

        if [ ! -f "$today" ]; then
            echo "   lane-$lane: today MISSING"
            continue
        fi
        if [ ! -f "$yesterday" ]; then
            echo "   lane-$lane: no yesterday cache"
            continue
        fi

        # Compare URLs to find new articles
        local result=$(python3 -c "
import json

with open('$today') as f:
    today_data = json.load(f)
with open('$yesterday') as f:
    yesterday_data = json.load(f)

today_urls = {a.get('url','') for a in today_data.get('articles',[])}
yesterday_urls = {a.get('url','') for a in yesterday_data.get('articles',[])}

new_urls = today_urls - yesterday_urls
new_articles = [a for a in today_data.get('articles',[]) if a.get('url','') in new_urls]

print(f'   lane-$lane: {len(today_urls)} total, {len(new_urls)} new, {len(yesterday_urls)} cached')
for a in new_articles[:5]:
    print(f'     🆕 {a.get(\"title\",\"?\")[:80]}')
" 2>/dev/null)
        echo "$result"

        new_count=$((new_count + $(echo "$result" | grep -c '🆕' || true)))
        total_count=$((total_count + $(echo "$result" | head -1 | grep -oP '\d+(?= total)' || echo 0)))
    done

    echo ""
    echo "═══════════════════════════════════════"
    echo "  Summary: $new_count new articles across $total_count total"
    echo "═══════════════════════════════════════"
}

# ═══════════════════════════════════════════════════
# clean — remove caches older than N days
# ═══════════════════════════════════════════════════
clean_cache() {
    local keep_days="${2:-30}"
    echo "🧹 Cleaning caches older than $keep_days days..."

    local cutoff
    if [[ "$OSTYPE" == "darwin"* ]]; then
        cutoff=$(date -j -v-${keep_days}d +%Y%m%d)
    else
        cutoff=$(date -d "$keep_days days ago" +%Y%m%d)
    fi

    local cleaned=0
    for cache_dir in "$CACHE_DIR"/*/; do
        local dir_date=$(basename "$cache_dir")
        if [[ "$dir_date" =~ ^[0-9]{8}$ ]] && [ "$dir_date" -lt "$cutoff" ]; then
            echo "   removing $dir_date"
            rm -rf "$cache_dir"
            cleaned=$((cleaned + 1))
        fi
    done

    echo "✓ Cleaned $cleaned caches (keeping last $keep_days days)"
}

# ═══════════════════════════════════════════════════
# Dispatch
# ═══════════════════════════════════════════════════
case "$ACTION" in
    save)  save_cache ;;
    diff)  diff_cache ;;
    clean) clean_cache "$@" ;;
    *)
        echo "Unknown action: $ACTION"
        echo "Usage: $0 {save|diff|clean} [YYYYMMDD|keep_days]"
        exit 1
        ;;
esac
