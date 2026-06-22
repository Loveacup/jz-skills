#!/usr/bin/env bash
# test-usage.sh — TDD test for cc-usage.sh (P0-2, PRD R8c)
#
# CC usage management: pre-mode snapshots cumulative ccusage totals into a baseline,
# post-mode reads the baseline and reports this turn's delta. ccusage has NO remaining
# quota (only Anthropic knows), so the script never fabricates a forecast — it reports
# actual cumulative/delta and always reminds the user to hit /usage for real remaining.
#
# All tests inject a stub via CC_USAGE_CMD → zero network, deterministic, <1s.
# Machine assertion line: stderr "USAGE_META mode=.. ccusage_ok=.. ..".

set -euo pipefail

USAGE="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-usage.sh"
SESSION="cctmux-test-usage"
BASELINE="/tmp/cc-usage-baseline-${SESSION}.json"
STUB="/tmp/cc-usage-stub-${SESSION}.sh"
FIX="/tmp/cc-usage-fixture-${SESSION}.json"
PASS=0 FAIL=0

cleanup() { rm -f "$BASELINE" "$STUB" "$FIX"; }
trap cleanup EXIT

# Stub that emits whatever is currently in $FIX (mutable between pre/post)
make_stub() {
  cat > "$STUB" <<EOF
#!/usr/bin/env bash
cat "$FIX"
EOF
  chmod +x "$STUB"
}
fixture() {  # fixture <totalTokens> <totalCost>
  printf '{"totals":{"totalTokens":%s,"totalCost":%s,"inputTokens":1,"outputTokens":1,"cacheCreationTokens":0,"cacheReadTokens":0}}\n' "$1" "$2" > "$FIX"
}

ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
no()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "=== cc-usage TDD: pre/post 用量基线与 delta (P0-2) ==="
echo ""

# ── TC1: pre writes a non-empty baseline with totalTokens ──
cleanup; make_stub; fixture 1000 1.0
CC_USAGE_CMD="bash $STUB" bash "$USAGE" --mode pre --task "demo" --effort high --session "$SESSION" >/dev/null 2>/dev/null || true
if [[ -s "$BASELINE" ]] && [[ "$(jq -er '.totalTokens' "$BASELINE" 2>/dev/null)" == "1000" ]]; then
  ok "TC1 pre → 基线文件存在且非空 (totalTokens=1000)"
else
  no "TC1 pre → 基线缺失/为空/字段错 (got: $(cat "$BASELINE" 2>/dev/null | head -c 80))"
fi

# ── TC2: post reads baseline and computes delta (1500-1000=500, 1.6-1.0=0.6) ──
cleanup; make_stub; fixture 1000 1.0
CC_USAGE_CMD="bash $STUB" bash "$USAGE" --mode pre --task "demo" --effort high --session "$SESSION" >/dev/null 2>/dev/null || true
fixture 1500 1.6   # consumption happened: totals advanced
post_err=$(CC_USAGE_CMD="bash $STUB" bash "$USAGE" --mode post --session "$SESSION" 2>&1 >/dev/null || true)
if grep -q 'deltaTokens=500' <<<"$post_err" && grep -q 'deltaCost=0\.6' <<<"$post_err"; then
  ok "TC2 post → delta 正确 (deltaTokens=500 · deltaCost≈0.6)"
else
  no "TC2 post → delta 错 (META: $(grep USAGE_META <<<"$post_err" | head -c 120))"
fi

# ── TC3: post with NO baseline → graceful degrade, exit 0, baseline=missing ──
cleanup; make_stub; fixture 1500 1.6
rm -f "$BASELINE"
set +e
post_err=$(CC_USAGE_CMD="bash $STUB" bash "$USAGE" --mode post --session "$SESSION" 2>&1 >/dev/null); rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -q 'baseline=missing' <<<"$post_err"; then
  ok "TC3 post 无基线 → 优雅降级 (exit 0 · baseline=missing)"
else
  no "TC3 post 无基线 → 未优雅降级 (rc=$rc · META: $(grep USAGE_META <<<"$post_err" | head -c 120))"
fi

# ── TC4: ccusage unavailable → fallback, exit 0, ccusage_ok=false, baseline still written ──
cleanup
set +e
pre_err=$(CC_USAGE_CMD="/bin/nonexistent-ccusage-xyz" bash "$USAGE" --mode pre --task "demo" --effort low --session "$SESSION" 2>&1 >/dev/null); rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -q 'ccusage_ok=false' <<<"$pre_err" && [[ -s "$BASELINE" ]]; then
  ok "TC4 ccusage 不可用 → fallback (exit 0 · ccusage_ok=false · 仍写最小基线)"
else
  no "TC4 ccusage 不可用 → 未降级 (rc=$rc · baseline_exists=$([[ -s "$BASELINE" ]] && echo y || echo n) · META: $(grep USAGE_META <<<"$pre_err" | head -c 120))"
fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
