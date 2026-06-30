#!/usr/bin/env bash
# cc-active-sessions.sh — 列出活跃 CC session 及其状态（Hermes 路由层前置查询）
#
# Usage: cc-active-sessions.sh [--json] [--topic <name>]
#
# Output modes:
#   default    — human-readable table (for Hermes to relay to user)
#   --json     — JSON array (for Hermes to parse programmatically)
#   --topic X  — filter to topic-mapped sessions only (reads /tmp/cc-topic-map.json)
#
# State source: /tmp/cc-status-<s>.json (hook authority), fallback heartbeat
#
# Hermetic: CC_ACTIVE_TMPDIR for test injection, CC_ACTIVE_TMUX for tmux stub.

set -euo pipefail
source "$(dirname "$0")/lib/portability.sh"

OUTPUT="table" TOPIC_FILTER="" TMP="${CC_ACTIVE_TMPDIR:-/tmp}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)  OUTPUT="json"; shift ;;
    --topic) TOPIC_FILTER="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

NOW=$(date +%s)
ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TMUX="${CC_ACTIVE_TMUX:-tmux}"

# ── 枚举 CC sessions ──────────────────────────────────────
SESSIONS=$($TMUX list-sessions -F '#{session_name}' 2>/dev/null | grep '^hermes-cc-' || true)

if [[ -z "$SESSIONS" ]]; then
  if [[ "$OUTPUT" == "json" ]]; then
    echo '[]'
  else
    echo "📭 无活跃 CC session"
  fi
  exit 0
fi

# ── Topic filter（R9b）────────────────────────────────────
if [[ -n "$TOPIC_FILTER" ]]; then
  TOPIC_MAP="${TMP}/cc-topic-map.json"
  if [[ -f "$TOPIC_MAP" ]] && command -v jq >/dev/null 2>&1; then
    MAPPED_SESSION=$(jq -r --arg t "$TOPIC_FILTER" '.[$t] // ""' "$TOPIC_MAP" 2>/dev/null || echo "")
    if [[ -n "$MAPPED_SESSION" && "$MAPPED_SESSION" != "null" ]]; then
      SESSIONS="$MAPPED_SESSION"
    else
      SESSIONS=""
    fi
  else
    SESSIONS=""
  fi
  if [[ -z "$SESSIONS" ]]; then
    if [[ "$OUTPUT" == "json" ]]; then
      echo '[]'
    else
      echo "📭 无 topic '$TOPIC_FILTER' 的 CC session"
    fi
    exit 0
  fi
fi

# ── 逐个读状态 ──────────────────────────────────────────
RESULTS=()
FIRST=true
if [[ "$OUTPUT" == "json" ]]; then printf '['; fi
for s in $SESSIONS; do
  [[ -z "$s" ]] && continue

  STATUS_F="${TMP}/cc-status-${s}.json"
  HB_F="${TMP}/cc-heartbeat-${s}"
  FREEZE_F="${TMP}/cc-freeze-${s}"
  TURNDONE_F="${TMP}/cc-turn-done-${s}"

  STATE="unknown" LAST_TOOL="" LAST_EVENT="" HB_AGE=-1 FREEZE=false TURN_DONE=false

  # Hook authority
  if [[ -f "$STATUS_F" ]] && command -v jq >/dev/null 2>&1; then
    STATE=$(jq -r '.state // "unknown"' "$STATUS_F" 2>/dev/null || echo "unknown")
    LAST_TOOL=$(jq -r '.last_tool // ""' "$STATUS_F" 2>/dev/null || echo "")
    LAST_EVENT=$(jq -r '.last_event // ""' "$STATUS_F" 2>/dev/null || echo "")
    [[ -z "$STATE" || "$STATE" == "null" ]] && STATE="unknown"
  fi

  # Heartbeat age
  if [[ -f "$HB_F" ]]; then
    HB_AGE=$(( NOW - $(get_mtime "$HB_F") ))
  fi

  # Auxiliary
  [[ -f "$FREEZE_F" ]] && FREEZE=true
  [[ -f "$TURNDONE_F" ]] && TURN_DONE=true

  # Emoji for human output
  case "$STATE" in
    IDLE)           EMOJI="💤" ;;
    TOOL)           EMOJI="⚡" ;;
    THINKING)       EMOJI="🧠" ;;
    WAITING_AGENTS) EMOJI="⏳" ;;
    COMPLETED)      EMOJI="✅" ;;
    BLOCKED)        EMOJI="🛑" ;;
    GONE|ERROR|SHELL) EMOJI="❌" ;;
    ACTIVE|RECEIVED) EMOJI="🔵" ;;
    COMPACTING)     EMOJI="🗜️" ;;
    *)              EMOJI="❓" ;;
  esac

  if [[ "$OUTPUT" == "json" ]]; then
    $FIRST || printf ','
    FIRST=false
    printf '{"session":"%s","state":"%s","last_tool":"%s","last_event":"%s","heartbeat_age_s":%s,"freeze":%s,"turn_done":%s}' \
      "$s" "$STATE" "$LAST_TOOL" "$LAST_EVENT" "$HB_AGE" "$FREEZE" "$TURN_DONE"
  else
    # Human table row
    EXTRA=""
    [[ "$FREEZE" == "true" ]] && EXTRA=" ⚠️冻结"
    [[ "$TURN_DONE" == "true" ]] && EXTRA="$EXTRA 📋完成"
    [[ -n "$LAST_TOOL" && "$LAST_TOOL" != "null" ]] && EXTRA="$EXTRA · $LAST_TOOL"
    printf '  %s  %-50s  %-12s  %s%s\n' "$EMOJI" "$s" "$STATE" "${HB_AGE}s" "$EXTRA"
  fi
done

if [[ "$OUTPUT" == "json" ]]; then
  echo ']'
fi

exit 0
