#!/usr/bin/env bash
# cc-route.sh — 消息路由层：Hermes 收到用户消息时，判断该如何对待 CC
#
# Usage: cc-route.sh --session <tmux-session-name> --intent <type>
#
# Intent types (classified by Hermes before calling):
#   new_task      — 全新独立任务，与 CC 当前工作无关
#   redirect      — 用户要改 CC 当前方向（"停，改做 X"）
#   status_query  — 用户只想了解进度
#   continuation  — CC 当前任务的补充上下文
#   unknown       — Hermes 无法分类，脚本给保守建议
#
# Output: JSON on stdout, machine metadata on stderr
#
# Design: 零 tmux 依赖，纯文件系统读取。状态来源优先级：
#   1. /tmp/cc-status-<s>.json (hook 权威，<120s 新鲜)
#   2. /tmp/cc-heartbeat-<s>    (fallback，<60s 新鲜)
#   3. 无 → unknown（无 CC）
#
# Injection points (hermetic testing):
#   CC_ROUTE_TMPDIR  — override /tmp for all signal files
#   CC_ROUTE_JQ      — override jq binary (default: jq)
#   CC_ROUTE_STATUS_MAX_AGE — status file freshness window (s, default 120)
#   CC_ROUTE_HB_MAX_AGE     — heartbeat freshness window (s, default 60)
#
# Decision matrix (state × intent → action):
#   IDLE              + new_task      → handle_directly
#   IDLE              + redirect      → forward_now
#   IDLE              + continuation  → forward_now
#   TOOL/THINKING/WAITING_AGENTS/RECEIVED/ACTIVE/COMPACTING + new_task → queue
#   TOOL              + redirect      → forward_now
#   TOOL              + continuation  → forward_now
#   THINKING (fresh)  + redirect      → queue
#   THINKING (freeze) + redirect      → interrupt  [confirm_required=true]
#   THINKING          + continuation  → queue
#   WAITING_AGENTS    + redirect      → queue
#   COMPLETED/GONE/ERROR/SHELL/unknown → handle_directly
#   BLOCKED           + redirect/continuation → forward_now
#   status_query (any state)          → report_status
#   unknown intent (any state)        → report_status(IDLE) / queue / handle_directly
#
# v1.1 changes:
#   P0-A: SHELL 归入 terminal（崩溃 CC 不排队）
#   P0-B: jq guard + CC_ROUTE_JQ 注入 + printf 降级 JSON
#   P1-A: 输出 status_age_s 字段
#   P1-B: 输出 confirm_required 字段（interrupt 时 true）
#   P1-C: HB_AGE 始终计算（独立于 state source）
#   P3-A: THINKING 不可达注释
#   P3-B: 无效 intent 值 stderr warn

set -euo pipefail
source "$(dirname "$0")/lib/portability.sh"

# P0-B: jq 可注入（CC_ROUTE_JQ），同 CC_USAGE_CMD / CC_WAIT_FSWATCH 模式
JQ="${CC_ROUTE_JQ:-jq}"

SESSION="" INTENT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="${2:-}"; shift 2 ;;
    --intent)  INTENT="${2:-}";  shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$SESSION" || -z "$INTENT" ]]; then
  echo '{"error":"--session and --intent required"}'
  exit 2
fi

# ── Configuration ───────────────────────────────────────────
TMP="${CC_ROUTE_TMPDIR:-/tmp}"
STATUS_F="${TMP}/cc-status-${SESSION}.json"
HB_F="${TMP}/cc-heartbeat-${SESSION}"
FREEZE_F="${TMP}/cc-freeze-${SESSION}"
TURNDONE_F="${TMP}/cc-turn-done-${SESSION}"
STATUS_MAX_AGE="${CC_ROUTE_STATUS_MAX_AGE:-120}"
HB_MAX_AGE="${CC_ROUTE_HB_MAX_AGE:-60}"
NOW=$(date +%s)
ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# ── State resolution ───────────────────────────────────────
CC_STATE="unknown"
STATE_SOURCE="none"
FREEZE=false
TURN_DONE=false
HB_AGE=-1
STATUS_AGE=-1

# P1-C: 心跳年龄始终计算（独立于 state source，用于输出一致性）
if [[ -f "$HB_F" ]]; then
  HB_AGE=$(( NOW - $(get_mtime "$HB_F") ))
fi

# Priority 1: hook-authored status file (fresh)
if [[ -f "$STATUS_F" ]]; then
  sm=$(get_mtime "$STATUS_F")
  STATUS_AGE=$(( NOW - sm ))
  if [[ "$STATUS_AGE" -lt "$STATUS_MAX_AGE" ]]; then
    if command -v "${JQ}" >/dev/null 2>&1; then
      CC_STATE=$("${JQ}" -r '.state // "unknown"' "$STATUS_F" 2>/dev/null || echo "unknown")
      [[ -z "$CC_STATE" || "$CC_STATE" == "null" ]] && CC_STATE="unknown"
      STATE_SOURCE="hook_status"
    fi
  fi
fi

# Priority 2: heartbeat fallback (status stale or missing)
if [[ "$STATE_SOURCE" == "none" ]]; then
  if [[ "$HB_AGE" -ge 0 && "$HB_AGE" -lt "$HB_MAX_AGE" ]]; then
    CC_STATE="ACTIVE"
    STATE_SOURCE="heartbeat"
  fi
fi

# Check auxiliary files
[[ -f "$FREEZE_F" ]] && FREEZE=true
[[ -f "$TURNDONE_F" ]] && TURN_DONE=true

# ── Decision engine ────────────────────────────────────────
# Terminal states: no CC or CC done/gone/error/crash → Hermes handles directly
# P0-A: SHELL（崩溃回落 shell）等价 ERROR，归入 terminal
is_terminal() {
  [[ "$CC_STATE" == "unknown"   || "$CC_STATE" == "COMPLETED" \
  || "$CC_STATE" == "GONE"      || "$CC_STATE" == "ERROR" \
  || "$CC_STATE" == "SHELL" ]]
}

# Forwardable states: CC is interruptible enough to accept typed input
is_forwardable() {
  [[ "$CC_STATE" == "IDLE" || "$CC_STATE" == "TOOL" || "$CC_STATE" == "BLOCKED" ]]
}

# Queue states: CC is busy in a way best left uninterrupted
is_queue_state() {
  [[ "$CC_STATE" == "THINKING"       || "$CC_STATE" == "WAITING_AGENTS" \
  || "$CC_STATE" == "RECEIVED"       || "$CC_STATE" == "ACTIVE" \
  || "$CC_STATE" == "COMPACTING" ]]
}

ACTION="" MECHANISM="" RISK="low" RATIONALE=""

case "$INTENT" in
  status_query)
    ACTION="report_status"
    MECHANISM="direct_reply"
    RATIONALE="用户要状态，直接汇报 CC 当前状态 (${CC_STATE})"
    ;;

  new_task)
    if is_terminal; then
      ACTION="handle_directly"
      MECHANISM="null"
      RATIONALE="CC 不在/已结束/异常，Hermes 独立处理新任务"
    elif [[ "$CC_STATE" == "IDLE" ]]; then
      ACTION="handle_directly"
      MECHANISM="null"
      RATIONALE="CC IDLE 无进行中任务，Hermes 独立处理新任务"
    else
      ACTION="queue"
      MECHANISM="cc-wait-marker"
      RATIONALE="CC 在 ${CC_STATE}，新任务排队等 turn-done"
    fi
    ;;

  redirect)
    if is_terminal; then
      ACTION="handle_directly"
      MECHANISM="null"
      RATIONALE="CC 不在/已结束/异常，Hermes 独立处理"
    elif [[ "$CC_STATE" == "IDLE" ]]; then
      ACTION="forward_now"
      MECHANISM="tmux_type+enter"
      RATIONALE="CC IDLE，直接转发重定向指令"
    elif [[ "$CC_STATE" == "THINKING" && "$FREEZE" == "true" ]]; then
      # §THINKING-unreachable: hooks 不写 THINKING（hook 盲区，见 AGENTS.md）。
      # 此分支为防御性代码——当前 hook 体系下 cc-status.json 不出现 THINKING；
      # 适用于未来 cc-monitor 开始回写 cc-status.json 的演进场景。
      ACTION="interrupt"
      MECHANISM="tmux_keys_escape+type+enter"
      RISK="medium"
      RATIONALE="CC THINKING 且已冻结 >3min，Escape 打断 + 转发重定向"
    elif [[ "$CC_STATE" == "TOOL" ]]; then
      ACTION="forward_now"
      MECHANISM="tmux_type+enter"
      RATIONALE="CC TOOL，工具调用可安全打断转发"
    elif [[ "$CC_STATE" == "BLOCKED" ]]; then
      ACTION="forward_now"
      MECHANISM="tmux_type+enter"
      RATIONALE="CC BLOCKED 等权限/输入，转发帮 CC 脱困"
    else
      ACTION="queue"
      MECHANISM="cc-wait-marker"
      RATIONALE="CC ${CC_STATE}，保守排队等 turn-done"
    fi
    ;;

  continuation)
    if is_terminal; then
      ACTION="handle_directly"
      MECHANISM="null"
      RATIONALE="CC 不在/已结束，Hermes 自行处理"
    elif is_forwardable; then
      ACTION="forward_now"
      MECHANISM="tmux_type+enter"
      RATIONALE="CC ${CC_STATE}，可直接转发补充上下文"
    else
      ACTION="queue"
      MECHANISM="cc-wait-marker"
      RATIONALE="CC ${CC_STATE}，补充上下文排队等 turn-done"
    fi
    ;;

  unknown|*)
    # P3-B: 区分合法 unknown（Hermes 无法分类）和非法 intent 值（调用方 bug）
    [[ "$INTENT" != "unknown" ]] && echo "ROUTEMETA warn=invalid_intent intent=${INTENT}" >&2
    if is_terminal; then
      ACTION="handle_directly"
      MECHANISM="null"
      RATIONALE="CC 不在/已结束"
    elif [[ "$CC_STATE" == "IDLE" ]]; then
      ACTION="report_status"
      MECHANISM="direct_reply"
      RATIONALE="CC IDLE，意图不明 → 先汇报状态等指令"
    else
      ACTION="queue"
      MECHANISM="cc-wait-marker"
      RATIONALE="意图不明 + CC 工作中，保守排队"
    fi
    ;;
esac

# P1-B: confirm_required — interrupt 需用户确认后执行（risk=medium 的硬信号）
CONFIRM_REQUIRED=false
[[ "$ACTION" == "interrupt" ]] && CONFIRM_REQUIRED=true

# ── Output JSON ─────────────────────────────────────────────
HB_FRESH=false
[[ "$HB_AGE" -ge 0 && "$HB_AGE" -lt "$HB_MAX_AGE" ]] && HB_FRESH=true

# P0-B: jq 不可用 → printf 降级 JSON（action=handle_directly, error=jq_unavailable）
# 决策：降级选最保守的 handle_directly（jq 坏了别碰 CC）
if ! command -v "${JQ}" >/dev/null 2>&1; then
  printf '{"session":"%s","cc_state":"%s","cc_state_source":"none","error":"jq_unavailable","user_intent":"%s","recommendation":{"action":"handle_directly","mechanism":"null","risk":"low","confirm_required":false,"rationale":"jq not available, conservative fallback"}}\n' \
    "$SESSION" "$CC_STATE" "$INTENT"
  echo "ROUTEMETA session=$SESSION cc_state=$CC_STATE intent=$INTENT action=handle_directly risk=low error=jq_unavailable" >&2
  exit 0
fi

"${JQ}" -n \
  --arg  session          "$SESSION" \
  --arg  cc_state         "$CC_STATE" \
  --arg  state_source     "$STATE_SOURCE" \
  --argjson hb_age        "$HB_AGE" \
  --argjson hb_fresh      "$HB_FRESH" \
  --argjson status_age    "$STATUS_AGE" \
  --argjson freeze        "$FREEZE" \
  --argjson turn_done     "$TURN_DONE" \
  --arg  intent           "$INTENT" \
  --arg  action           "$ACTION" \
  --arg  mechanism        "$MECHANISM" \
  --arg  risk             "$RISK" \
  --argjson confirm_required "$CONFIRM_REQUIRED" \
  --arg  rationale        "$RATIONALE" \
  --arg  ts               "$ISO" \
  '{
    session:          $session,
    cc_state:         $cc_state,
    cc_state_source:  $state_source,
    heartbeat_age_s:  $hb_age,
    heartbeat_fresh:  $hb_fresh,
    status_age_s:     $status_age,
    freeze:           $freeze,
    turn_done:        $turn_done,
    user_intent:      $intent,
    recommendation: {
      action:           $action,
      mechanism:        $mechanism,
      risk:             $risk,
      confirm_required: $confirm_required,
      rationale:        $rationale
    },
    ts: $ts
  }'

echo "ROUTEMETA session=$SESSION cc_state=$CC_STATE source=$STATE_SOURCE intent=$INTENT action=$ACTION risk=$RISK" >&2
exit 0
