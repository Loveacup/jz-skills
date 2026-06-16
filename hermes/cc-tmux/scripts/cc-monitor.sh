#!/usr/bin/env bash
# cc-monitor.sh — Capture CC tmux pane, emit a COPY-PASTE-READY 📡 block,
#                 and MECHANICALLY record monitoring (heartbeat + state log).
#
# Usage: cc-monitor.sh --session <name> [--last-timestamp <ISO>]
#
# v1.3 enforcement contract (files keyed by session, under /tmp):
#   cc-heartbeat-<session>     single-line snapshot:
#                              EPOCH|RUNCOUNT|STATE|TOKENS|TOKCHG_EPOCH|SEQ|THINK_TIME
#                              (THINK_TIME added for freeze detection — see line ~156)
#   cc-state-<session>.log     append-only JSONL, ONE LINE PER RUN
#                              (field "changed":true marks a real state transition)
# cc-finish.sh audits these (freshness + transition summary + gaps).
# eval-compliance.sh scores relay density against monitor run count.
#
# RELAY CONTRACT (answers "format compliance is poor"):
#   stdout between the ===📡 BEGIN / ===📡 END=== markers is FOR THE USER.
#   Relay it VERBATIM — do not summarize, batch, or reformat. Machine metadata
#   goes to stderr so "relay all of stdout" is always exactly right.

set -euo pipefail

SESSION="" LAST_TS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --last-timestamp) LAST_TS="$2"; shift 2 ;;   # back-compat; heartbeat now authoritative
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "Usage: cc-monitor.sh --session <name>" >&2
  exit 1
fi

HB="/tmp/cc-heartbeat-${SESSION}"
STATELOG="/tmp/cc-state-${SESSION}.log"
NOW=$(date +%s)
ISO=$(date -u +%Y-%m-%dT%H:%M:%S)

# ── Read previous snapshot (for diff / freeze / counters) ────
PREV_EPOCH=0; RUNCOUNT=0; PREV_STATE="NONE"; PREV_TOKENS="?"; TOKCHG_EPOCH=$NOW; SEQ=0; PREV_THINK_TIME="?"
if [[ -f "$HB" ]]; then
  IFS='|' read -r PREV_EPOCH RUNCOUNT PREV_STATE PREV_TOKENS TOKCHG_EPOCH SEQ PREV_THINK_TIME < "$HB" 2>/dev/null || true
  [[ -z "${PREV_EPOCH:-}" ]] && PREV_EPOCH=0
  [[ -z "${RUNCOUNT:-}" ]] && RUNCOUNT=0
  [[ -z "${PREV_STATE:-}" ]] && PREV_STATE="NONE"
  [[ -z "${PREV_TOKENS:-}" ]] && PREV_TOKENS="?"
  [[ -z "${TOKCHG_EPOCH:-}" ]] && TOKCHG_EPOCH=$NOW
  [[ -z "${SEQ:-}" ]] && SEQ=0
  [[ -z "${PREV_THINK_TIME:-}" ]] && PREV_THINK_TIME="?"
fi
RUNCOUNT=$((RUNCOUNT + 1))
SEQ=$((SEQ + 1))
DELTA=$((NOW - PREV_EPOCH)); [[ "$PREV_EPOCH" -eq 0 ]] && DELTA=0

# persist(STATE, TOKENS, TOKCHG_EPOCH, THINK_TIME): write heartbeat + append run to JSONL log
persist() {
  local st="$1" tk="$2" tce="$3" tt="$4" changed="false"
  [[ "$st" != "$PREV_STATE" ]] && changed="true"
  echo "${NOW}|${RUNCOUNT}|${st}|${tk}|${tce}|${SEQ}|${tt}" > "$HB"
  printf '{"ts":"%s","epoch":%s,"seq":%s,"state":"%s","from":"%s","changed":%s,"tokens":"%s","delta_s":%s}\n' \
    "$ISO" "$NOW" "$SEQ" "$st" "$PREV_STATE" "$changed" "$tk" "$DELTA" >> "$STATELOG"
  # stderr: machine metadata (NOT for relay)
  echo "META session=$SESSION seq=$SEQ run=$RUNCOUNT state=$st changed=$changed heartbeat=$HB statelog=$STATELOG TIMESTAMP=$ISO" >&2
}

# ── Session existence ────────────────────────────────────────
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  persist "GONE" "$PREV_TOKENS" "$TOKCHG_EPOCH" "$PREV_THINK_TIME"
  echo "===📡 BEGIN (relay verbatim)==="
  echo "📡 CC #${SEQ} · session '$SESSION' NOT FOUND (exited/killed)"
  echo "   → 若非预期：可能崩溃；若预期结束：跑 cc-finish.sh 收尾"
  echo "===📡 END==="
  exit 1
fi

# ── Capture pane ─────────────────────────────────────────────
PANE=$(tmux capture-pane -t "$SESSION" -p -S -40 2>/dev/null || echo "")
LASTLINE=$(printf '%s\n' "$PANE" | grep -v '^[[:space:]]*$' | tail -1 || true)

if [[ -z "$PANE" ]]; then
  persist "STARTING" "?" "$NOW" "?"
  echo "===📡 BEGIN (relay verbatim)==="
  echo "📡 CC #${SEQ} [距上次 ${DELTA}s] · 空 pane（session 刚起）"
  echo "===📡 END==="
  exit 0
fi

# ── Signals ──────────────────────────────────────────────────
BYPASS=$(printf '%s' "$PANE" | grep -o 'bypass permissions on' | head -1 || true)
# §3.1 fix: narrow THINKING/TOOL to active tail (last 6 non-empty lines)
# to avoid stale signals in scrollback after CC finishes a turn.
ACTIVE_TAIL=$(printf '%s\n' "$PANE" | grep -v '^[[:space:]]*$' | tail -6 || true)
THINKING=$(printf '%s' "$ACTIVE_TAIL" | grep -oE '[✻✳✶✢✽]' | tail -1 || true)
TOOL_CALL=$(printf '%s' "$ACTIVE_TAIL" | grep -oE '⏺|●' | tail -1 || true)
WAIT_AGENTS=$(printf '%s' "$PANE" | grep -oE 'Waiting for [0-9]+ background agent' | tail -1 || true)
TOKENS=$(printf '%s' "$PANE" | grep -oE '[0-9.]+k tokens' | tail -1 || echo "?")
# Elapsed-time progress proxy. Read ONLY from the live spinner line (in ACTIVE_TAIL)
# so a stray "5s"/"3m" in tool output can't spoof progress and mask a real freeze.
# Cover every timer rendering: "2m 3s" (full) · "49m · thinking" (minutes-only,
# Pitfall #14's xhigh-freeze form) · "37s" (sub-minute). Feeds the freeze clock so a
# "?"-token long-think with a ticking timer is not flagged as a false freeze.
SPINNER_LINE=$(printf '%s\n' "$ACTIVE_TAIL" | grep -E '[✻✳✶✢✽]' | tail -1 || true)
THINK_TIME=$(printf '%s' "$SPINNER_LINE" | grep -oE '[0-9]+m [0-9]+s|[0-9]+m|[0-9]+s' | tail -1 || echo "?")
ALMOST_DONE=$(printf '%s' "$PANE" | grep -o 'almost done' | head -1 || true)
ERROR=$(printf '%s' "$PANE" | grep -oE 'API Error|✗ [A-Za-z].*|Traceback \(most recent' | tail -1 || true)

# Prompt line: the ❯ input prompt only renders when CC is WAITING for input, so an
# empty ❯ near the bottom is a reliable IDLE signal that beats a stale `●` in
# scrollback (a finished session always keeps `●` history — old bug source).
# Look only at the last 3 non-empty lines so we don't catch a scrolled-up prompt.
LAST3=$(printf '%s\n' "$PANE" | grep -v '^[[:space:]]*$' | tail -3 || true)
PROMPT_LINE=$(printf '%s\n' "$LAST3" | grep '❯' | tail -1 || true)
PROMPT_CONTENT=""
if [[ -n "$PROMPT_LINE" ]]; then
  PROMPT_CONTENT=$(printf '%s' "$PROMPT_LINE" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//')
fi
# IDLE = a ❯ prompt is at the bottom and is empty (no residual text after it)
# §3.1 fix: tighten IDLE so it is mutually exclusive with any active-work signal
# (THINKING/TOOL/WAIT_AGENTS). Defense-in-depth: the priority chain below also
# resolves TOOL/THINKING before IDLE, but the guard keeps the IDLE flag itself
# honest for any future consumer ("三者互锁，缺一不可").
IDLE=""
if [[ -n "$PROMPT_LINE" && -z "$PROMPT_CONTENT" \
      && -z "$THINKING" && -z "$TOOL_CALL" && -z "$WAIT_AGENTS" ]]; then
  IDLE="yes"
fi

# Crash-to-shell heuristic: no bypass banner AND last line looks like a bare shell prompt
SHELL_FALLBACK=""
if [[ -z "$BYPASS" && -z "$PROMPT_LINE" ]]; then
  if printf '%s' "$LASTLINE" | grep -qE '[%$#][[:space:]]*$'; then
    SHELL_FALLBACK="yes"
  fi
fi

# ── Resolve primary STATE (priority order) ───────────────────
# §3.1 fix: TOOL/THINKING now win over IDLE. TOOL/THINKING signals
# are sampled from ACTIVE_TAIL (last 6 non-empty lines) to avoid stale
# scrollback artifacts. IDLE only fires when no active work signal exists.
if [[ -n "$SHELL_FALLBACK" ]]; then
  STATE="SHELL"
elif [[ -n "$WAIT_AGENTS" ]]; then
  STATE="WAITING_AGENTS"
elif [[ -n "$TOOL_CALL" ]]; then
  STATE="TOOL"
elif [[ -n "$THINKING" ]]; then
  STATE="THINKING"
elif [[ -n "$IDLE" ]]; then
  STATE="IDLE"
elif [[ -n "$BYPASS" ]]; then
  STATE="IDLE"
else
  STATE="STARTING"
fi

# ── Token-freeze tracking (folds audit gap #4 into the script) ──
# THINK_TIME progression (CC's own per-second timer) resets the freeze clock
# even when TOKENS stays "?" (composing mode where token count is unreadable).
# Only alert when BOTH TOKENS and THINK_TIME are stuck — true freeze.
if [[ "$TOKENS" != "$PREV_TOKENS" || "$STATE" != "$PREV_STATE" || "$THINK_TIME" != "$PREV_THINK_TIME" ]]; then
  TOKCHG_EPOCH=$NOW          # tokens/state/think_time moved → reset freeze clock
fi
FREEZE_S=$((NOW - TOKCHG_EPOCH))

# ── Persist BEFORE printing (so a relay never lacks a record) ──
persist "$STATE" "$TOKENS" "$TOKCHG_EPOCH" "$THINK_TIME"

# ── Output 📡 block (copy-paste-ready, between markers) ───────
TRANS=""
[[ "$STATE" != "$PREV_STATE" && "$PREV_STATE" != "NONE" ]] && TRANS="  🔀 ${PREV_STATE} → ${STATE}"

echo "===📡 BEGIN (relay verbatim)==="
echo "📡 CC #${SEQ} [距上次 ${DELTA}s]"
[[ -n "$TRANS" ]] && echo "$TRANS"
case "$STATE" in
  SHELL)
    echo "  ⛔ CC 疑似崩溃回落 shell（无 bypass 横幅）：${LASTLINE:0:80}"
    echo "  → 别误判为完成。检查崩溃原因或 cc-finish.sh --force 收尾"
    ;;
  WAITING_AGENTS)
    echo "  ⏳ Leader: ${WAIT_AGENTS}（等后台 worker）"
    echo "  📊 Tokens: $TOKENS"
    if [[ "$FREEZE_S" -gt 120 ]]; then
      echo "  ⚠️ worker token 冻结 ${FREEZE_S}s → 先 ls -la 查产出文件，有则告知 CC，无则可能真死"
    fi
    ;;
  IDLE)
    echo "  💤 Leader: idle（❯ 空，就绪/可能已完成）"
    ;;
  TOOL)
    TOOL_LINE=$(printf '%s\n' "$PANE" | grep -E '⏺|●' | tail -1 | sed 's/^[[:space:]]*//' | cut -c1-100)
    echo "  ⚡ Leader: $TOOL_LINE"
    echo "  📊 Tokens: $TOKENS"
    ;;
  THINKING)
    if [[ -n "$ALMOST_DONE" ]]; then
      echo "  ⚡ Leader: ${THINKING} Thinking…（${THINK_TIME} · ${TOKENS} · almost done）"
    else
      echo "  ⚡ Leader: ${THINKING} Thinking…（${THINK_TIME} · ${TOKENS}）"
    fi
    if [[ "$FREEZE_S" -gt 180 ]]; then
      echo "  ⚠️ token 冻结 ${FREEZE_S}s（>3min）→ 考虑 Ctrl+C 缩小范围重问"
    fi
    ;;
  STARTING)
    echo "  ⏯️ Leader: 启动中/处理中…  📊 Tokens: $TOKENS"
    ;;
esac
[[ -n "$ERROR" ]] && echo "  ❌ 疑似错误: ${ERROR:0:80}"
[[ -n "$BYPASS" ]] && echo "  🔓 Bypass: on"
[[ "$DELTA" -gt 120 ]] && echo "  ⏰ 距上次汇报 >120s（监控间隙，cc-finish 会标记）"
echo "===📡 END==="

exit 0
