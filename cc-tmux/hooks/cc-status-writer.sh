#!/usr/bin/env bash
# cc-status-writer.sh — P1-1 Hook 成状态权威
#
# 所有 hook 事件统一调此脚本：从 stdin 的 hook JSON + $1=<EVENT> 推断状态，
# 原子写入权威状态文件 /tmp/cc-status-<key>.json，并刷新心跳（兼容旧 reader）。
#
# Usage (settings.runtime.json 接线)：
#   <event hook command>; ...; in_passed_through | bash $CC_TMUX_HOOK_DIR/cc-status-writer.sh <EVENT>
#   实际接线里本脚本作为该事件 hooks 数组的【附加 command】，自己 in=$(cat) 读 stdin。
#
# 设计要点：
#   · EVENT 走【参数】（settings 知道接的是哪个事件），不依赖 stdin 的 .hook_event_name
#     （CC v2.1.178 未保证该字段存在）。
#   · D-4 key = ${CC_TMUX_SESSION:-<stdin .session_id>}（CLAUDE_SESSION_ID 在 hook env 恒空）。
#   · stdin 只能读一次 → in=$(cat) 一次性吞，之后所有 jq 喂 "$in"。
#   · 原子写：temp + mv（PreToolUse async 高频，reader 永不见半成品）。
#   · 仅负责 status 文件 + heartbeat。turn-done/state-log/re-block 仍归现有 hook（不双主）。
#   · 非 deny，恒 exit 0，静默降级（绝不 wedge turn）。
#   · CC_STATUS_TMPDIR 覆盖文件基目录（默认 /tmp）——测试注入。

EVENT="${1:-unknown}"
in=$(cat 2>/dev/null || echo "")

sid=$(printf '%s' "$in" | jq -r '.session_id // "unknown"' 2>/dev/null || echo "unknown")
[[ -z "$sid" || "$sid" == "null" ]] && sid="unknown"
K="${CC_TMUX_SESSION:-$sid}"
TOOL=$(printf '%s' "$in" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
[[ "$TOOL" == "null" ]] && TOOL=""
# SessionStart 携带 .source（startup/resume/clear/compact）——compact = 压缩后续接，
# 是「新 resume ID 已生成」的事后信号（CC 无 PostCompact 事件，靠 SessionStart:compact 识别）。
SRC=$(printf '%s' "$in" | jq -r '.source // empty' 2>/dev/null || echo "")
[[ "$SRC" == "null" ]] && SRC=""

TMP="${CC_STATUS_TMPDIR:-/tmp}"
STATUS="${TMP}/cc-status-${K}.json"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# ── event → state 映射（当前接线 8 事件：PreToolUse/PostToolUse/UserPromptSubmit/
#    Notification/SessionStart/SessionEnd/Stop/PreCompact；其余为 future-compat，未接线）──
case "$EVENT" in
  PreToolUse|PostToolUse)                          STATE="TOOL" ;;
  # future-compat（未接线）：
  PostToolUseFailure|SubagentStart|SubagentStop)   STATE="TOOL" ;;
  Notification)
    STATE="IDLE"
    printf '%s' "$in" | grep -qi 'permission' && STATE="BLOCKED" || true
    ;;
  UserPromptSubmit)             STATE="RECEIVED" ;;
  Stop)                         STATE="COMPLETED" ;;
  PreCompact)                   STATE="COMPACTING" ;;   # 压缩前：TUI 将暂停，标 COMPACTING 避免 watcher 误判 freeze
  SessionStart)                 STATE="ACTIVE" ;;       # source=compact 时压缩已完成、session 续接 → 仍 ACTIVE，仅 last_event 标注
  SessionEnd)                   STATE="GONE" ;;
  # future-compat（未接线）：
  StopFailure)                  STATE="ERROR" ;;
  # future-compat（未接线）：
  PermissionRequest|PermissionDenied) STATE="BLOCKED" ;;
  *)                            STATE="ACTIVE" ;;
esac

# last_event 标注：SessionStart:compact 让 cc-monitor/cc-finish 看出这次 ACTIVE 是压缩续接
EV_LABEL="$EVENT"
[[ "$EVENT" == "SessionStart" && "$SRC" == "compact" ]] && EV_LABEL="SessionStart:compact"

# ── 读上一版（state_since 同态续接 + seq 自增 + last_tool 续接）──
PREV_STATE=""; PREV_SINCE=""; PREV_SEQ=0; PREV_TOOL=""; PREV_TOOL_SINCE=""
if [[ -f "$STATUS" ]]; then
  PREV_STATE=$(jq -r '.state // ""'           "$STATUS" 2>/dev/null || echo "")
  PREV_SINCE=$(jq -r '.state_since // ""'      "$STATUS" 2>/dev/null || echo "")
  PREV_SEQ=$(jq -r '.seq // 0'                 "$STATUS" 2>/dev/null || echo 0)
  PREV_TOOL=$(jq -r '.last_tool // ""'         "$STATUS" 2>/dev/null || echo "")
  PREV_TOOL_SINCE=$(jq -r '.last_tool_since // ""' "$STATUS" 2>/dev/null || echo "")
fi
[[ "$PREV_SEQ" =~ ^[0-9]+$ ]] || PREV_SEQ=0
SEQ=$((PREV_SEQ + 1))

# state_since：状态不变 → 续旧；状态变 → 置 NOW
if [[ "$STATE" == "$PREV_STATE" && -n "$PREV_SINCE" ]]; then SINCE="$PREV_SINCE"; else SINCE="$NOW"; fi

# last_tool：本事件带 tool_name → 用之（变了才刷 since）；否则续上一版已知 tool
if [[ -n "$TOOL" ]]; then
  if [[ "$TOOL" == "$PREV_TOOL" && -n "$PREV_TOOL_SINCE" ]]; then TOOL_SINCE="$PREV_TOOL_SINCE"; else TOOL_SINCE="$NOW"; fi
else
  TOOL="$PREV_TOOL"; TOOL_SINCE="$PREV_TOOL_SINCE"
fi

# ── 原子写：jq -n 构造 → temp → mv ──
tmpf="${STATUS}.tmp.$$"
if jq -n \
    --arg state "$STATE" --arg since "$SINCE" --arg ev "$EV_LABEL" \
    --arg tool "$TOOL" --arg toolsince "$TOOL_SINCE" --argjson seq "$SEQ" --arg hb "$NOW" \
    '{state:$state, state_since:$since, last_event:$ev, last_tool:$tool, last_tool_since:$toolsince, seq:$seq, heartbeat:$hb}' \
    > "$tmpf" 2>/dev/null; then
  mv -f "$tmpf" "$STATUS" 2>/dev/null || rm -f "$tmpf" 2>/dev/null
else
  rm -f "$tmpf" 2>/dev/null
fi

# ── 兼容：同时刷心跳（旧 heartbeat reader 继续工作）──
touch "${TMP}/cc-heartbeat-${K}" 2>/dev/null || true

exit 0
