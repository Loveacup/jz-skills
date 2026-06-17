#!/usr/bin/env bash
# test-monitor-freeze.sh — TDD test for cc-monitor.sh freeze-detection fix
#
# Verifies that when TOKENS="?" (CC composing) but THINK_TIME is still
# ticking, the freeze clock is reset — preventing false "token freeze" alerts.
#
# RED test: Should FAIL before the fix, GREEN after.

set -euo pipefail

MONITOR="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-monitor.sh"
SESSION="cctmux-test-freeze"
PASS=0 FAIL=0

cleanup() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  rm -f "/tmp/cc-heartbeat-${SESSION}" "/tmp/cc-state-${SESSION}.log" \
        "/tmp/cc-fixture-${SESSION}.txt" "/tmp/cc-monitor-stderr-${SESSION}.txt" \
        "/tmp/cc-freeze-${SESSION}"
}
trap cleanup EXIT

check_freeze_reset() {
  local name="$1" fixture_a="$2" fixture_b="$3" expect_reset="$4"
  
  cleanup
  
  # Round 1: establish baseline with fixture_a
  printf '%s\n' "$fixture_a" > "/tmp/cc-fixture-${SESSION}.txt"
  tmux new-session -d -s "$SESSION" -x 120 -y 20 \
    "while true; do cat /tmp/cc-fixture-${SESSION}.txt 2>/dev/null; sleep 0.2; done" 2>/dev/null
  sleep 0.8

  # §Phase-2: --force-capture so the fresh-heartbeat fast path never short-circuits the
  # probe — freeze detection IS the probe path the watcher drives.
  bash "$MONITOR" --session "$SESSION" --force-capture >/dev/null 2>/dev/null || true

  # Artificially age the TOKCHG_EPOCH to simulate >180s freeze
  local hb="/tmp/cc-heartbeat-${SESSION}"
  if [[ -f "$hb" ]]; then
    local old_tce
    IFS='|' read -r _ __ ___ ____ old_tce _____ < "$hb" 2>/dev/null || true
    local aged_tce=$((old_tce - 200))  # push 200s into the past
    # Rewrite heartbeat with aged TOKCHG_EPOCH
    local fields
    IFS='|' read -r f1 f2 f3 f4 _ f6 < "$hb" 2>/dev/null || true
    printf '%s|%s|%s|%s|%d|%s\n' "${f1:-0}" "${f2:-0}" "${f3:-NONE}" "${f4:-?}" "$aged_tce" "${f6:-0}" > "$hb"
  fi
  
  # Round 2: update fixture to fixture_b (THINK_TIME progressed, TOKENS still "?")
  printf '%s\n' "$fixture_b" > "/tmp/cc-fixture-${SESSION}.txt"
  sleep 0.3

  bash "$MONITOR" --session "$SESSION" --force-capture >/dev/null 2>/dev/null || true
  
  # Check: TOKCHG_EPOCH should be recent (close to NOW), meaning freeze was reset
  local now new_tce
  now=$(date +%s)
  if [[ -f "$hb" ]]; then
    IFS='|' read -r _ __ ___ ____ new_tce ______ < "$hb" 2>/dev/null || true
    local age=$((now - new_tce))
    
    if [[ "$expect_reset" == "yes" ]]; then
      if [[ "$age" -lt 30 ]]; then
        echo "  ✅ $name → freeze reset (TOKCHG_EPOCH age=${age}s < 30s)"
        PASS=$((PASS+1))
      else
        echo "  ❌ $name → freeze NOT reset (TOKCHG_EPOCH age=${age}s)"
        FAIL=$((FAIL+1))
      fi
    else
      if [[ "$age" -gt 100 ]]; then
        echo "  ✅ $name → freeze correctly NOT reset (TOKCHG_EPOCH age=${age}s > 100s)"
        PASS=$((PASS+1))
      else
        echo "  ❌ $name → freeze incorrectly reset (TOKCHG_EPOCH age=${age}s)"
        FAIL=$((FAIL+1))
      fi
    fi
  else
    echo "  ❌ $name → heartbeat missing"
    FAIL=$((FAIL+1))
  fi
  
  cleanup
}

echo "=== cc-monitor TDD: Freeze Detection Fix (THINK_TIME progression) ==="
echo ""

# Test 1: TOKENS="?" but THINK_TIME progressed → freeze should reset
check_freeze_reset \
  "? token + THINK_TIME progressing" \
  "✻ Thinking…（1m 0s · ?）" \
  "✻ Thinking…（1m 30s · ?）" \
  "yes"

# Test 2: TOKENS and THINK_TIME both unchanged → freeze should NOT reset
check_freeze_reset \
  "? token + THINK_TIME frozen (true freeze)" \
  "✻ Thinking…（2m 0s · ?）" \
  "✻ Thinking…（2m 0s · ?）" \
  "no"

# Test 3: TOKENS changed (normal) → always reset
check_freeze_reset \
  "TOKENS changing (normal progression)" \
  "✻ Thinking…（3m 0s · 1.5k tokens）" \
  "✻ Thinking…（3m 30s · 2.1k tokens）" \
  "yes"

# Test 4: sub-minute "37s" timer (no "Nm" prefix) progressing → must reset.
# Old regex '[0-9]+m [0-9]+s' misses seconds-only timers → RED before broadening.
check_freeze_reset \
  "sub-minute seconds-only timer progressing" \
  "✻ Thinking… (37s · ?)" \
  "✻ Thinking… (45s · ?)" \
  "yes"

# Test 5: Pitfall #14 minutes-only form "(49m · thinking some more)" progressing → must reset.
# Old regex misses "Xm" without a trailing "Ns" → RED before broadening. This is the
# EXACT xhigh-freeze rendering, where a live long-think must NOT trip a false alarm.
check_freeze_reset \
  "minutes-only timer (Pitfall #14 form) progressing" \
  "✢ Inferring… (49m · thinking some more)" \
  "✢ Inferring… (50m · thinking some more)" \
  "yes"

# Test 6: minutes-only timer FROZEN + "?" token → true freeze, must NOT reset.
# Guards that broadening the match did not lose freeze detection for this form.
check_freeze_reset \
  "minutes-only timer frozen (true freeze)" \
  "✢ Inferring… (49m · thinking some more)" \
  "✢ Inferring… (49m · thinking some more)" \
  "no"

# ─── §Phase-2: a confirmed freeze writes /tmp/cc-freeze-<s> (Hermes's passive alert) ───
echo ""
echo "§Phase-2 freeze marker — confirmed freeze writes a marker; recovery clears it"
cleanup
printf '✻ Thinking…（2m 0s · ?）\n' > "/tmp/cc-fixture-${SESSION}.txt"
tmux new-session -d -s "$SESSION" -x 120 -y 20 \
  "while true; do cat /tmp/cc-fixture-${SESSION}.txt; sleep 0.2; done" 2>/dev/null
sleep 0.8
bash "$MONITOR" --session "$SESSION" --force-capture >/dev/null 2>/dev/null || true
# Age TOKCHG_EPOCH ~300s into the past (mirror check_freeze_reset: the 6th read var
# absorbs SEQ|THINK_TIME, so the 7-field schema is preserved on rewrite).
HBF="/tmp/cc-heartbeat-${SESSION}"
IFS='|' read -r g1 g2 g3 g4 _ g6 < "$HBF" 2>/dev/null || true
printf '%s|%s|%s|%s|%d|%s\n' "${g1:-0}" "${g2:-0}" "${g3:-THINKING}" "${g4:-?}" "$(( $(date +%s) - 300 ))" "${g6:-0}" > "$HBF"
bash "$MONITOR" --session "$SESSION" --force-capture >/dev/null 2>/dev/null || true
if [[ -f "/tmp/cc-freeze-${SESSION}" ]]; then
  echo "  ✅ confirmed freeze (THINKING >180s) → cc-freeze marker written"; PASS=$((PASS+1))
else
  echo "  ❌ freeze marker NOT written"; FAIL=$((FAIL+1))
fi
# Recovery: THINK_TIME progresses → freeze clock resets → marker must be cleared
printf '✻ Thinking…（9m 9s · ?）\n' > "/tmp/cc-fixture-${SESSION}.txt"; sleep 0.4
bash "$MONITOR" --session "$SESSION" --force-capture >/dev/null 2>/dev/null || true
if [[ ! -f "/tmp/cc-freeze-${SESSION}" ]]; then
  echo "  ✅ recovery (THINK_TIME progresses) → freeze marker cleared"; PASS=$((PASS+1))
else
  echo "  ❌ freeze marker NOT cleared on recovery"; FAIL=$((FAIL+1))
fi
cleanup

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
rm -f /tmp/cc-monitor-stderr-*.txt
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
