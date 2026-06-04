#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# diff-check.sh — 早新闻 CSS 渲染前差异检查
# 用法: ./diff-check.sh <current-html> [baseline-css]
# 返回: 0=通过 (偏差<5%), 1=警告 (≥5%), 2=错误
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

THRESHOLD=5
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
BASELINE="${2:-$SKILL_DIR/assets/mobile-baseline.css}"

# ── Colors ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ── Args check ──
CURRENT="${1:-}"
if [ -z "$CURRENT" ]; then
    echo "Usage: $0 <current-html-file> [baseline-css-file]"
    exit 2
fi
if [ ! -f "$CURRENT" ]; then
    echo -e "${RED}✗ Current HTML not found: $CURRENT${NC}"
    exit 2
fi
if [ ! -f "$BASELINE" ]; then
    echo -e "${YELLOW}⚠ No baseline CSS found at $BASELINE${NC}"
    echo -e "${YELLOW}  Run with --init to create baseline from current HTML.${NC}"
    if [ "${1:-}" = "--init" ]; then
        extract_css "$CURRENT" > "$BASELINE"
        echo -e "${GREEN}✓ Baseline created: $BASELINE${NC}"
        exit 0
    fi
    exit 2
fi

# ── Extract CSS from HTML ──
extract_css() {
    sed -n '/<style>/,/<\/style>/p' "$1" \
        | sed '1d;$d' \
        | sed 's/\/\*.*\*\///g' \
        | sed '/^[[:space:]]*$/d' \
        | sed 's/[[:space:]]\+/ /g' \
        | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# ── Extract CSS properties (key:value pairs only) ──
# macOS grep lacks -P, use perl for portability
extract_props() {
    perl -ne 'while (/([a-z-]+)\s*:\s*([^;]+)/g) { print "$1: $2\n" }' "$1" 2>/dev/null \
        | sed 's/[[:space:]]\+$//' \
        | sort -u
}

# ── Main ──
TMPDIR="$(mktemp -d)"
trap "rm -rf $TMPDIR" EXIT

# Extract and normalize
extract_css "$CURRENT" > "$TMPDIR/current.css"
cp "$BASELINE" "$TMPDIR/baseline.css"

CURRENT_PROPS="$TMPDIR/current.props"
BASELINE_PROPS="$TMPDIR/baseline.props"

extract_props "$TMPDIR/current.css" > "$CURRENT_PROPS" 2>/dev/null || true
extract_props "$TMPDIR/baseline.css" > "$BASELINE_PROPS" 2>/dev/null || true

TOTAL_BASELINE=$(wc -l < "$BASELINE_PROPS" | tr -d ' ')
TOTAL_CURRENT=$(wc -l < "$CURRENT_PROPS" | tr -d ' ')

if [ "$TOTAL_BASELINE" -eq 0 ]; then
    echo -e "${RED}✗ Baseline has 0 properties — corrupted?${NC}"
    exit 2
fi

# Count differences
CHANGED=$(comm -13 "$BASELINE_PROPS" "$CURRENT_PROPS" | wc -l | tr -d ' ')
REMOVED=$(comm -23 "$BASELINE_PROPS" "$CURRENT_PROPS" | wc -l | tr -d ' ')
TOTAL_DIFF=$((CHANGED + REMOVED))

# Deviation = changed properties / total baseline properties * 100
DEVIATION=$(echo "scale=1; $TOTAL_DIFF * 100 / $TOTAL_BASELINE" | bc)

echo "═══════════════════════════════════════"
echo "  CSS Diff Check — Morning News Briefing"
echo "═══════════════════════════════════════"
echo "  Baseline props : $TOTAL_BASELINE"
echo "  Current props  : $TOTAL_CURRENT"
echo "  Changed        : $CHANGED"
echo "  Removed        : $REMOVED"
echo "  Deviation      : ${DEVIATION}%"
echo "  Threshold      : ${THRESHOLD}%"
echo "═══════════════════════════════════════"

if [ "$(echo "$DEVIATION >= $THRESHOLD" | bc)" -eq 1 ]; then
    echo ""
    echo -e "${RED}✗ DEVIATION EXCEEDS THRESHOLD${NC}"
    echo ""
    echo "  New/Changed properties:"
    if [ "$CHANGED" -gt 0 ]; then
        comm -13 "$BASELINE_PROPS" "$CURRENT_PROPS" | head -20 | sed 's/^/    + /'
    fi
    echo ""
    echo "  Removed properties:"
    if [ "$REMOVED" -gt 0 ]; then
        comm -23 "$BASELINE_PROPS" "$CURRENT_PROPS" | head -20 | sed 's/^/    - /'
    fi
    echo ""
    echo -e "${YELLOW}  ⟳ Falling back to baseline CSS.${NC}"
    echo -e "${YELLOW}    To accept new CSS as baseline:${NC}"
    echo -e "${YELLOW}    $0 $CURRENT --accept${NC}"
    exit 1
else
    echo -e "${GREEN}✓ PASS — deviation ${DEVIATION}% < ${THRESHOLD}% threshold${NC}"
fi

# ── Handle --accept ──
if [ "${2:-}" = "--accept" ] || [ "${3:-}" = "--accept" ]; then
    extract_css "$CURRENT" > "$BASELINE"
    echo -e "${GREEN}✓ Baseline updated: $BASELINE${NC}"
fi
