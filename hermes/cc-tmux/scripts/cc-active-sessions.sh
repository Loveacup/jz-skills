#!/usr/bin/env bash
# cc-active-sessions.sh — 列出活跃 CC session 及其状态（Hermes 路由层前置查询）
#
# Usage: cc-active-sessions.sh [--json] [--topic <name>] [--inventory]
#
# Output modes:
#   default     — human-readable table (for Hermes to relay to user)
#   --json      — JSON array (for Hermes to parse programmatically)
#   --topic X   — filter to topic-mapped primary session only (reads /tmp/cc-topic-map.json)
#   --inventory — read-only tmux inventory: include managed hermes-cc-* plus suspected Claude panes
#
# State source: /tmp/cc-status-<s>.json (hook authority), fallback heartbeat.
#
# Resource-model boundary:
#   - managed  = hermes-cc-* session; current lifecycle authority.
#   - suspected = non-managed tmux session whose pane command/title looks like Claude; report only.
#   - pane/window are presentation/support, not CC worker identity.
#   - topic-map currently supports legacy string, current {session, at}, and future {primary:{session}} reads.
#     This script does not write or migrate topic-map schema.
#
# Hermetic: CC_ACTIVE_TMPDIR for test injection, CC_ACTIVE_TMUX for tmux stub.

set -euo pipefail
source "$(dirname "$0")/lib/portability.sh"

OUTPUT="table" TOPIC_FILTER="" TMP="${CC_ACTIVE_TMPDIR:-/tmp}" INVENTORY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)      OUTPUT="json"; shift ;;
    --topic)     TOPIC_FILTER="${2:-}"; shift 2 ;;
    --inventory) INVENTORY=true; shift ;;
    *) shift ;;
  esac
done

NOW=$(date +%s)
TMUX="${CC_ACTIVE_TMUX:-tmux}"

session_name() {
  local line="$1"
  printf '%s' "${line%%|*}"
}

session_attached() {
  local line="$1"
  if [[ "$line" == *"|"* ]]; then printf '%s' "${line#*|}"; else printf '0'; fi
}

resolve_topic_session() {
  local topic="$1" map="${TMP}/cc-topic-map.json"
  [[ -f "$map" ]] || return 0
  command -v jq >/dev/null 2>&1 || return 0
  jq -r --arg t "$topic" '
    .[$t] // empty
    | if type == "string" then .
      elif type == "object" then (.session // .primary.session // empty)
      else empty end
  ' "$map" 2>/dev/null || true
}

pane_summary() {
  local s="$1"
  $TMUX list-panes -t "$s" -F '#{pane_id}|#{pane_pid}|#{pane_current_command}|#{pane_current_path}|#{pane_title}' 2>/dev/null | head -1 || true
}

looks_like_claude_pane() {
  local s="$1" panes
  panes=$($TMUX list-panes -s -t "$s" -F '#{pane_current_command}|#{pane_title}' 2>/dev/null || true)
  printf '%s\n' "$panes" | grep -Eiq '(^|[|[:space:]])claude([|[:space:]]|$)|Claude Code|bypass permissions on'
}

emit_empty() {
  if [[ "$OUTPUT" == "json" ]]; then
    echo '[]'
  else
    if [[ -n "$TOPIC_FILTER" ]]; then
      echo "📭 无 topic '$TOPIC_FILTER' 的 CC session"
    else
      echo "📭 无活跃 CC session"
    fi
  fi
}

# ── 枚举 tmux sessions ──────────────────────────────────────
RAW_SESSIONS=$($TMUX list-sessions -F '#{session_name}|#{session_attached}' 2>/dev/null || true)

# ── Topic filter（R9b / future-read compatible）──────────────
if [[ -n "$TOPIC_FILTER" ]]; then
  MAPPED_SESSION=$(resolve_topic_session "$TOPIC_FILTER")
  if [[ -n "$MAPPED_SESSION" && "$MAPPED_SESSION" != "null" ]]; then
    FILTERED_SESSIONS=""
    while IFS= read -r line; do
      if [[ "$(session_name "$line")" == "$MAPPED_SESSION" ]]; then
        FILTERED_SESSIONS+="$line"$'\n'
      fi
    done <<< "$RAW_SESSIONS"
    RAW_SESSIONS="$FILTERED_SESSIONS"
  else
    RAW_SESSIONS=""
  fi
fi

# ── Filter: default only managed; inventory includes suspected ───────────
SESSIONS=""
if [[ -n "$RAW_SESSIONS" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    s=$(session_name "$line")
    [[ -z "$s" ]] && continue
    if [[ "$s" == hermes-cc-* ]]; then
      SESSIONS+="$line"$'\n'
    elif [[ "$INVENTORY" == true ]] && looks_like_claude_pane "$s"; then
      SESSIONS+="$line"$'\n'
    fi
  done <<< "$RAW_SESSIONS"
fi

if [[ -z "$SESSIONS" ]]; then
  emit_empty
  exit 0
fi

# ── 逐个读状态 ──────────────────────────────────────────
FIRST=true
if [[ "$OUTPUT" == "json" ]]; then printf '['; fi
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  s=$(session_name "$line")
  ATTACHED=$(session_attached "$line")
  CLASSIFICATION="managed"
  EVIDENCE="session_name"
  if [[ "$s" != hermes-cc-* ]]; then
    CLASSIFICATION="suspected"
    EVIDENCE="pane_command_or_title"
  fi

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
    if [[ "$INVENTORY" == true ]]; then
      printf '{"session":"%s","state":"%s","last_tool":"%s","last_event":"%s","heartbeat_age_s":%s,"freeze":%s,"turn_done":%s,"classification":"%s","evidence":"%s","session_attached":%s}' \
        "$s" "$STATE" "$LAST_TOOL" "$LAST_EVENT" "$HB_AGE" "$FREEZE" "$TURN_DONE" "$CLASSIFICATION" "$EVIDENCE" "${ATTACHED:-0}"
    else
      printf '{"session":"%s","state":"%s","last_tool":"%s","last_event":"%s","heartbeat_age_s":%s,"freeze":%s,"turn_done":%s}' \
        "$s" "$STATE" "$LAST_TOOL" "$LAST_EVENT" "$HB_AGE" "$FREEZE" "$TURN_DONE"
    fi
  else
    # Human table row
    EXTRA=""
    [[ "$FREEZE" == "true" ]] && EXTRA=" ⚠️冻结"
    [[ "$TURN_DONE" == "true" ]] && EXTRA="$EXTRA 📋完成"
    [[ -n "$LAST_TOOL" && "$LAST_TOOL" != "null" ]] && EXTRA="$EXTRA · $LAST_TOOL"
    [[ "$INVENTORY" == true ]] && EXTRA="$EXTRA · $CLASSIFICATION/$EVIDENCE · attached=${ATTACHED:-0}"
    printf '  %s  %-50s  %-12s  %s%s\n' "$EMOJI" "$s" "$STATE" "${HB_AGE}s" "$EXTRA"
  fi
done <<< "$SESSIONS"

if [[ "$OUTPUT" == "json" ]]; then
  echo ']'
fi

exit 0
