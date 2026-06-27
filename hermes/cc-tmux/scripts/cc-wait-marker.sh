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
#   · poll interval 2s
#
# Defaults: --after 0 (any marker newer than the epoch), --timeout 21600 (6h).

set -euo pipefail
source "$(dirname "$0")/lib/portability.sh"

usage() {
  cat >&2 <<'EOF'
Usage: cc-wait-marker.sh --session <tmux-session-name> [--after <unix_ts>] [--timeout <secs>]
  Blocks until /private/tmp/cc-turn-done-<session> has mtime strictly greater than
  --after, then prints the marker contents and exits 0.
    --after    baseline unix timestamp (default 0); wait for mtime > this value
    --timeout  max seconds to block (default 21600 = 6h); on expiry exit 1
  Exit codes: 0 newer marker found · 1 timeout · 2 bad/missing args
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
FSW_CAP="${CC_WAIT_FSW_CAP:-3}"         # 每次 fswatch 等待的看门狗上限（秒）：兜底 TOCTOU 漏检
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
