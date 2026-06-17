#!/usr/bin/env bash
# eval-compliance.sh — Machine-checkable compliance eval for cc-tmux skill (v1.4 / §Phase-3)
#
# Scores 3 symptoms against the artifacts the other scripts leave on disk:
#   occupancy     — was a cc-start.sh occupancy lock claimed?  (lock dir / transcript)
#   reporting     — §Phase-3 PASSIVE model: completion was SIGNALLED (turn-done) and no
#                   freeze alert was MISSED. (Replaces the old poll-density metric.)
#   verification  — disk-checked artifacts AND no silent crash-to-shell
#
# Why the reporting rescore (v1.4): the old metric divided cc-monitor run-count by
# session duration to reward dense polling. But Phase 2 moved the monitoring cadence
# off the LLM onto the watcher daemon + hooks — so rewarding poll density now penalises
# the intended passive behaviour. We instead score the event-driven protocol: did a
# turn-done completion signal appear, and was every cc-freeze alert acknowledged.
#
# Usage:
#   eval-compliance.sh --mode baseline|test --transcript <file>
#                      [--target <name>] [--session <name>]
# Output: JSON compliance report on stdout.
#
# NOTE: intentionally NOT `set -e`. Every grep-miss below is expected; aborting
# mid-script would emit truncated, invalid JSON — worse than a wrong field.
set -uo pipefail

MODE="" TRANSCRIPT="" TARGET="jz-skills" SESSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)       MODE="$2"; shift 2 ;;
    --transcript) TRANSCRIPT="$2"; shift 2 ;;
    --target)     TARGET="$2"; shift 2 ;;
    --session)    SESSION="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────
int_or() { [[ "${1:-}" =~ ^[0-9]+$ ]] && printf '%s' "$1" || printf '%s' "$2"; }

# ── Resolve session + artifact paths ─────────────────────────
# If --session omitted, recover it from the transcript (first hermes-cc-* name).
if [[ -z "$SESSION" && -f "$TRANSCRIPT" ]]; then
  SESSION=$(grep -oE 'hermes-cc-[A-Za-z0-9._-]+' "$TRANSCRIPT" 2>/dev/null | head -1)
fi
HB="/tmp/cc-heartbeat-${SESSION}"
STATELOG="/tmp/cc-state-${SESSION}.log"
LOCKDIR="/tmp/cc-lock-${TARGET}"

# ── 1. Occupancy: lock dir present now, OR cc-start evidence in transcript ──
score_occupancy() {
  if [[ -d "$LOCKDIR" ]]; then echo "pass"; return; fi
  if [[ -f "$TRANSCRIPT" ]] && \
     grep -qE "cc-lock-${TARGET}|cc-start\.sh|mkdir.*cc-lock|BUSY" "$TRANSCRIPT" 2>/dev/null; then
    echo "pass"; return
  fi
  echo "fail"
}

# ── 2. Responsiveness (§Phase-3 passive model) ───────────────
# Sets globals: REPORT_STATUS SOURCE TURN_DONE_EVIDENCE BUS_ALIVE FREEZE_UNHANDLED
#
# We NO LONGER score cc-monitor poll DENSITY. The watcher now owns the monitoring
# cadence (a deterministic shell loop), and the hooks keep the heartbeat fresh — so
# "Hermes polled often" is no longer the right thing to reward; it would penalise the
# very passive behaviour the architecture was changed to enable. Instead score the
# event-driven protocol:
#   TURN_DONE_EVIDENCE — completion was SIGNALLED: a /tmp/cc-turn-done-<s> marker exists
#                        OR the transcript shows Hermes used the turn-done flow.
#   FREEZE_UNHANDLED   — a /tmp/cc-freeze-<s> alert lingers AND the transcript never
#                        acknowledges it → a MISSED alert (the one thing that fails).
#   BUS_ALIVE          — heartbeat present → the hook/watcher bus ran (advisory).
score_reporting() {
  SOURCE="event-bus"
  TURN_DONE_EVIDENCE=false
  if [[ -f "/tmp/cc-turn-done-${SESSION}" ]] \
     || { [[ -f "$TRANSCRIPT" ]] && grep -qiE 'cc-turn-done|turn[_-]done' "$TRANSCRIPT" 2>/dev/null; }; then
    TURN_DONE_EVIDENCE=true
  fi
  BUS_ALIVE=false
  [[ -f "$HB" ]] && BUS_ALIVE=true
  FREEZE_UNHANDLED=false
  if [[ -f "/tmp/cc-freeze-${SESSION}" ]] \
     && ! { [[ -f "$TRANSCRIPT" ]] && grep -qiE 'cc-freeze|freeze|冻结' "$TRANSCRIPT" 2>/dev/null; }; then
    FREEZE_UNHANDLED=true
  fi
  # PASS = completion was signalled AND no freeze was missed. A transcript-only run
  # (v4 baseline, no heartbeat/marker) fails unless it shows the turn-done flow — so the
  # baseline-vs-test comparison still discriminates, just on the RIGHT axis.
  if [[ "$TURN_DONE_EVIDENCE" == true && "$FREEZE_UNHANDLED" == false ]]; then
    REPORT_STATUS="pass"
  else
    REPORT_STATUS="fail"
  fi
}

# ── 3. Verification: disk-check evidence AND no crash-to-shell ──
# Sets globals: VERIFY_STATUS DISK_CHECK CRASH_DETECTED
score_verification() {
  DISK_CHECK=false
  if [[ -f "$TRANSCRIPT" ]] && \
     grep -qE 'ls -la.*(output|cc-)|find -L|find.*-newer|wc -c.*cc-|磁盘校验|cc-finish\.sh' "$TRANSCRIPT" 2>/dev/null; then
    DISK_CHECK=true
  fi
  # SHELL state in the log == CC fell back to a bare shell (crash). Completing on a
  # crash without noticing is a verification failure, not a success.
  CRASH_DETECTED=false
  if [[ -f "$STATELOG" ]] && grep -q '"state":"SHELL"' "$STATELOG" 2>/dev/null; then
    CRASH_DETECTED=true
  fi
  if [[ "$DISK_CHECK" == true && "$CRASH_DETECTED" == false ]]; then
    VERIFY_STATUS="pass"
  else
    VERIFY_STATUS="fail"
  fi
}

# ── Main ─────────────────────────────────────────────────────
if [[ -z "$TRANSCRIPT" || ! -f "$TRANSCRIPT" ]]; then
  # Still allow file-based scoring, but bail clearly if there's nothing to score.
  if [[ ! -f "$HB" ]]; then
    printf '{"error":"transcript not found and no heartbeat","transcript":"%s","session":"%s"}\n' \
      "$TRANSCRIPT" "$SESSION"
    exit 1
  fi
fi

OCCUPANCY=$(score_occupancy)
score_reporting
score_verification

PASSES=0; TOTAL=3
[[ "$OCCUPANCY"     == "pass" ]] && PASSES=$((PASSES + 1))
[[ "$REPORT_STATUS" == "pass" ]] && PASSES=$((PASSES + 1))
[[ "$VERIFY_STATUS" == "pass" ]] && PASSES=$((PASSES + 1))

SCORE=$(echo "scale=1; $PASSES / $TOTAL * 100" | bc 2>/dev/null || echo "$((PASSES * 100 / TOTAL))")

cat <<EOF
{
  "mode": "$MODE",
  "target": "$TARGET",
  "session": "$SESSION",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S)",
  "score": ${SCORE},
  "passes": ${PASSES},
  "total": ${TOTAL},
  "checks": {
    "occupancy": "$OCCUPANCY",
    "reporting": {
      "status": "$REPORT_STATUS",
      "source": "$SOURCE",
      "turn_done_evidence": ${TURN_DONE_EVIDENCE},
      "bus_alive": ${BUS_ALIVE},
      "freeze_unhandled": ${FREEZE_UNHANDLED}
    },
    "verification": {
      "status": "$VERIFY_STATUS",
      "disk_check": ${DISK_CHECK},
      "crash_detected": ${CRASH_DETECTED}
    }
  }
}
EOF
