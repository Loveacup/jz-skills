#!/usr/bin/env bash
# eval-compliance.sh — Machine-checkable compliance eval for cc-tmux skill (v1.3)
#
# Scores 3 symptoms against the artifacts the other scripts leave on disk:
#   occupancy     — was a cc-start.sh occupancy lock claimed?  (lock dir / transcript)
#   reporting     — DENSITY, not just presence: ≥1 📡 relay per 120s of session
#   verification  — disk-checked artifacts AND no silent crash-to-shell
#
# Why density (v1.3): `count >= 1` let a single 📡 block "pass" a 30-min session.
# We now divide monitor run-count by real session duration so sparse monitoring
# fails. Authoritative source is cc-monitor.sh's heartbeat + state log; when those
# are absent (e.g. a v4 baseline run that never calls cc-monitor.sh) we degrade to
# counting relay markers in the transcript so baseline-vs-test stays comparable.
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

iso_to_epoch() { date -j -f "%Y-%m-%dT%H:%M:%S" "$1" +%s 2>/dev/null || echo 0; }

# Span (seconds) between the first and last ISO timestamp found in a file.
transcript_span_s() {
  local f="$1" first last fe le
  [[ -f "$f" ]] || { echo 0; return; }
  first=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' "$f" 2>/dev/null | head -1)
  last=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' "$f" 2>/dev/null | tail -1)
  [[ -z "$first" || -z "$last" ]] && { echo 0; return; }
  fe=$(iso_to_epoch "$first"); le=$(iso_to_epoch "$last")
  local d=$(( le - fe )); [[ "$d" -lt 0 ]] && d=0
  echo "$d"
}

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

# ── 2. Reporting density ─────────────────────────────────────
# Sets globals: REPORT_STATUS RUNS DURATION DENSITY MINREQ SOURCE
score_reporting() {
  if [[ -f "$HB" ]]; then
    SOURCE="heartbeat"
    # heartbeat line: EPOCH|RUNCOUNT|STATE|TOKENS|TOKCHG_EPOCH|SEQ  (RUNCOUNT = field 2)
    local _e rc
    IFS='|' read -r _e rc _ _ _ _ < "$HB" 2>/dev/null
    RUNS=$(int_or "$rc" 0)
    # duration = last epoch − first epoch from the state log
    local first last span
    first=$(grep -oE '"epoch":[0-9]+' "$STATELOG" 2>/dev/null | head -1 | grep -oE '[0-9]+')
    last=$(grep -oE '"epoch":[0-9]+'  "$STATELOG" 2>/dev/null | tail -1 | grep -oE '[0-9]+')
    first=$(int_or "$first" 0); last=$(int_or "$last" 0)
    span=$(( last - first )); [[ "$span" -lt 0 ]] && span=0
    if [[ "$span" -ge 1 ]]; then
      DURATION="$span"
    else
      # A single state-log point can't reveal a long session — fall back to the
      # transcript span so "monitored once near the end" cannot pass.
      DURATION=$(int_or "$(transcript_span_s "$TRANSCRIPT")" 0)
    fi
  else
    # Fallback: no heartbeat (e.g. v4 baseline). Count relay markers + estimate
    # duration from transcript timestamps so the comparison still works.
    SOURCE="transcript"
    local begins lines
    begins=$(grep -c '===📡 BEGIN' "$TRANSCRIPT" 2>/dev/null); begins=$(int_or "$begins" 0)
    if [[ "$begins" -gt 0 ]]; then
      RUNS="$begins"
    else
      lines=$(grep -c '📡' "$TRANSCRIPT" 2>/dev/null); RUNS=$(int_or "$lines" 0)
    fi
    DURATION=$(int_or "$(transcript_span_s "$TRANSCRIPT")" 0)
  fi

  [[ "$DURATION" -lt 1 ]] && DURATION=1            # avoid div-by-zero

  # density_score = min(100, RUNCOUNT * 120 * 100 / duration_s)
  DENSITY=$(( RUNS * 120 * 100 / DURATION ))
  [[ "$DENSITY" -gt 100 ]] && DENSITY=100
  # min reports required to clear the "1 per 120s" cadence (ceil)
  MINREQ=$(( (DURATION + 119) / 120 )); [[ "$MINREQ" -lt 1 ]] && MINREQ=1

  if [[ "$DENSITY" -ge 100 ]]; then REPORT_STATUS="pass"; else REPORT_STATUS="fail"; fi
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
      "heartbeat_runs": ${RUNS},
      "session_duration_s": ${DURATION},
      "min_required": ${MINREQ},
      "density_score": ${DENSITY}
    },
    "verification": {
      "status": "$VERIFY_STATUS",
      "disk_check": ${DISK_CHECK},
      "crash_detected": ${CRASH_DETECTED}
    }
  }
}
EOF
