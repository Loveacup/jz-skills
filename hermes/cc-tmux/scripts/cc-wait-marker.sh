#!/usr/bin/env bash
# cc-wait-marker.sh — Block until CC writes a turn-done marker NEWER than --after
# §3 In-Turn Wait: lets Hermes `process(action=wait)` on this inside ONE turn and
# loop send → wait → read → send, instead of ending the turn and re-injecting.
#
# Usage:
#   cc-wait-marker.sh --session <tmux-session-name> [--after <unix_ts>] [--timeout <secs>]
#
# Contract:
#   · marker path = /private/tmp/cc-turn-done-<session>   (/private/tmp, not /tmp:
#     macOS /tmp is a symlink and FSEvents/mtime resolve through /private/tmp)
#   · blocks until mtime(marker) > --after  (STRICT >, so a marker equal to the
#     baseline you already saw does NOT trigger — you must record --after as the
#     mtime/epoch BEFORE sending the next instruction; see Pitfall: mtime 比较)
#   · on a strictly-newer marker → print its contents (cat, no jq) and exit 0
#   · on --timeout expiry        → exit 1
#   · on bad/missing args        → exit 2 (+ stderr usage)
#   · on not-started gate fail   → exit 4 (IDLE / input residual; prevents 900s empty waits)
#   · poll interval 2s
#
# Defaults: --after 0 (any marker newer than the epoch), --timeout 21600 (6h).
# Startup gate: unless CC_WAIT_SKIP_START_GATE=1, refuse to wait on an unstarted task.

set -euo pipefail
source "$(dirname "$0")/lib/portability.sh"

usage() {
  cat >&2 <<'EOF'
Usage: cc-wait-marker.sh --session <tmux-session-name> [--after <unix_ts>] [--timeout <secs>]
  Blocks until /private/tmp/cc-turn-done-<session> has mtime strictly greater than
  --after, then prints the marker contents and exits 0.
    --after    baseline unix timestamp (default 0); wait for mtime > this value
    --timeout  max seconds to block (default 21600 = 6h); on expiry exit 1
  Startup gate: before waiting, detects IDLE / input residual / queued-message states
  and exits 4 instead of hanging on an unsubmitted task. Set
  CC_WAIT_AUTO_SUBMIT_RESIDUAL=1 only when the visible residual is known to be the
  freshly-sent task line and you want one automatic Enter retry.
  Exit codes: 0 newer marker found · 1 timeout · 2 bad/missing args · 4 not-started gate
EOF
}

SESSION="" AFTER=0 TIMEOUT=21600

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) [[ $# -ge 2 ]] || { echo "❌ cc-wait-marker: --session requires a value" >&2; usage; exit 2; }; SESSION="$2"; shift 2 ;;
    --after)   [[ $# -ge 2 ]] || { echo "❌ cc-wait-marker: --after requires a value"   >&2; usage; exit 2; }; AFTER="$2";   shift 2 ;;
    --timeout) [[ $# -ge 2 ]] || { echo "❌ cc-wait-marker: --timeout requires a value" >&2; usage; exit 2; }; TIMEOUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "❌ cc-wait-marker: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "❌ cc-wait-marker: --session is required" >&2
  usage
  exit 2
fi

if ! [[ "$AFTER" =~ ^[0-9]+$ ]]; then
  echo "❌ cc-wait-marker: --after must be a non-negative integer (got: '$AFTER')" >&2
  usage
  exit 2
fi

if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
  echo "❌ cc-wait-marker: --timeout must be a non-negative integer (got: '$TIMEOUT')" >&2
  usage
  exit 2
fi

MARKER="/private/tmp/cc-turn-done-${SESSION}"
POLL_FALLBACK=2        # 契约：fallback 轮询间隔（不变）
POLL_CREATE=0.5        # fswatch 模式下「等文件被创建」的短轮询（fswatch 监听不了空路径）
FSWATCH="${CC_WAIT_FSWATCH:-fswatch}"   # P1-2: 可注入（测试 stub）
WAIT_TMUX="${CC_WAIT_TMUX:-tmux}"       # v1.38: 可注入（startup gate 测试 stub）
FSW_CAP="${CC_WAIT_FSW_CAP:-3}"         # 每次 fswatch 等待的看门狗上限（秒）：兜底 TOCTOU 漏检
START_GRACE="${CC_WAIT_START_GRACE:-5}" # v1.38: 补 Enter 后等待 CC 离开 IDLE 的窗口
start=$(date +%s)

# marker 是否存在且 mtime 严格 > AFTER
is_newer() {
  [[ -f "$MARKER" ]] || return 1
  local m; m=$(get_mtime "$MARKER")
  [[ "$m" -gt "$AFTER" ]]
}
emit_and_exit0() { cat "$MARKER" 2>/dev/null || true; exit 0; }
timed_out() { [[ $(( $(date +%s) - start )) -ge "$TIMEOUT" ]]; }
exit_timeout() {
  echo "⏱  cc-wait-marker: timeout after ${TIMEOUT}s — no marker newer than ${AFTER} (session=${SESSION})" >&2
  exit 1
}

# v1.38 startup gate: 防止「任务文本留在输入框、wait-marker 空等 900s」。
# 返回：RUNNING/IDLE/RESIDUAL/QUEUE/UNKNOWN
status_state() {
  local sf="/tmp/cc-status-${SESSION}.json" age state
  [[ -f "$sf" ]] || { echo ""; return; }
  age=$(( $(date +%s) - $(get_mtime "$sf") ))
  [[ "$age" -gt "${CC_WAIT_STATUS_MAX_AGE:-120}" ]] && { echo ""; return; }
  if command -v jq >/dev/null 2>&1; then
    state=$(jq -r '.state // ""' "$sf" 2>/dev/null || echo "")
  else
    state=$(sed -n 's/.*"state"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$sf" | head -1)
  fi
  echo "$state"
}

pane_start_state() {
  local pane last prompt content ss
  pane=$($WAIT_TMUX capture-pane -t "$SESSION" -p -S -12 2>/dev/null || echo "")
  [[ -z "$pane" ]] && { echo "UNKNOWN"; return; }
  if printf '%s' "$pane" | grep -q 'Press up to edit queued'; then echo "QUEUE"; return; fi

  # 先判输入框残留。残留文本里可能包含 Write/Edit/Tool 等词，不能先 grep RUNNING。
  last=$(printf '%s\n' "$pane" | grep -v '^[[:space:]]*$' | tail -4)
  prompt=$(printf '%s\n' "$last" | grep '❯' | tail -1 || true)
  if [[ -n "$prompt" ]]; then
    content=$(printf '%s' "$prompt" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//')
    [[ -n "$content" ]] && { echo "RESIDUAL"; return; }
  fi

  # hook 状态优先于 scrollback 关键词；避免旧输出把 idle prompt 误判为 running。
  ss=$(status_state)
  case "$ss" in
    TOOL|THINKING|WAITING_AGENTS|ACTIVE|RECEIVED|COMPACTING|BLOCKED) echo "RUNNING"; return ;;
    IDLE|COMPLETED|GONE|ERROR|SHELL) echo "IDLE"; return ;;
  esac

  # 无新鲜 hook 时，仅在没有 prompt 的情况下用运行符号兜底。
  if [[ -z "$prompt" ]] && printf '%s' "$pane" | grep -qE '⏺|●|✻|✳|✶|✢|✽|Thinking|Reading|Edit|Write|Tool'; then
    echo "RUNNING"; return
  fi
  [[ -n "$prompt" ]] && { echo "IDLE"; return; }
  echo "UNKNOWN"
}

startup_gate() {
  [[ "${CC_WAIT_SKIP_START_GATE:-}" == "1" ]] && return 0
  is_newer && return 0

  local st deadline
  st=$(pane_start_state)
  case "$st" in
    RUNNING|UNKNOWN) return 0 ;;
    QUEUE)
      echo "❌ cc-wait-marker: CC input is in queued-message mode; refusing to wait on unsubmitted task (session=${SESSION})" >&2
      echo "   Fix: Escape/C-c 清队列后用单行指令重发。" >&2
      exit 4 ;;
    RESIDUAL)
      if [[ "${CC_WAIT_AUTO_SUBMIT_RESIDUAL:-}" != "1" ]]; then
        echo "❌ cc-wait-marker: pane has residual input; refusing to auto-submit unknown text (session=${SESSION})" >&2
        echo "   Fix: if this is the freshly-sent task line, set CC_WAIT_AUTO_SUBMIT_RESIDUAL=1 or press Enter explicitly; if stale, /clear then resend." >&2
        exit 4
      fi
      echo "⚠️  cc-wait-marker: pane has residual input; CC_WAIT_AUTO_SUBMIT_RESIDUAL=1 so sending Enter once (session=${SESSION})" >&2
      $WAIT_TMUX send-keys -t "$SESSION" Enter 2>/dev/null || true
      deadline=$(( $(date +%s) + START_GRACE ))
      while [[ $(date +%s) -lt "$deadline" ]]; do
        sleep 1
        is_newer && return 0
        st=$(pane_start_state)
        [[ "$st" == "RUNNING" || "$st" == "UNKNOWN" ]] && return 0
      done
      echo "❌ cc-wait-marker: task still not started after opt-in auto-Enter (${START_GRACE}s); refusing long wait (session=${SESSION})" >&2
      exit 4 ;;
    IDLE)
      echo "❌ cc-wait-marker: session is IDLE and no newer turn-done marker exists; task was not submitted (session=${SESSION})" >&2
      echo "   Fix: send task first, or if text is visible in input box, press Enter; then rerun wait-marker." >&2
      exit 4 ;;
  esac
}
startup_gate

# ── 原轮询模式（契约保底；fswatch 不可用 / CC_WAIT_MODE=fallback 时走这里）──
poll_loop() {
  while true; do
    is_newer && emit_and_exit0
    timed_out && exit_timeout
    sleep "$POLL_FALLBACK"
  done
}

# ── 决定模式：强制 fallback / fswatch 不在 PATH → 轮询 ──
if [[ "${CC_WAIT_MODE:-}" == "fallback" ]] || ! command -v "$FSWATCH" >/dev/null 2>&1; then
  poll_loop   # never returns
fi

# ── P1-2 fswatch 事件驱动（两阶段：等创建短轮询 → fswatch -1 等变更）──
while true; do
  # 1) 已满足 → 立即返回（含「一开始就已更新」的 Test 3 路径）
  is_newer && emit_and_exit0
  # 2) 超时预算横跨所有阶段与多次 fswatch 重入
  timed_out && exit_timeout
  remaining=$(( TIMEOUT - ($(date +%s) - start) ))
  [[ "$remaining" -le 0 ]] && exit_timeout

  # 3) 文件不存在：fswatch 监听不了空路径 → 短轮询等创建
  if [[ ! -f "$MARKER" ]]; then
    sleep "$POLL_CREATE"
    continue
  fi

  # 4) 文件存在但未更新：fswatch -1 阻塞等下一次变更。真事件 → fswatch 即时返回（事件驱动）。
  #    看门狗用 min(remaining, FSW_CAP) 上限：堵住 TOCTOU 漏检——marker 若在 is_newer 检查后、
  #    fswatch 起监听前就被写，fswatch 会空等「不存在的下一次事件」，看门狗 ≤FSW_CAP 内回顶复判。
  #    不靠 fswatch 退出码区分「真事件 vs 被 kill」（信号码不可靠）——一律回循环顶复判。
  cap="$remaining"; [[ "$cap" -gt "$FSW_CAP" ]] && cap="$FSW_CAP"
  "$FSWATCH" -1 "$MARKER" >/dev/null 2>&1 &
  FPID=$!
  ( sleep "$cap"; kill "$FPID" 2>/dev/null ) &
  TPID=$!
  wait "$FPID" 2>/dev/null || true       # set -e: fswatch 被 kill→143，须守护
  kill "$TPID" 2>/dev/null || true       # 真事件返回时清理还在睡的 sleeper（防泄漏）
  wait "$TPID" 2>/dev/null || true
done
