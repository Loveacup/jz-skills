#!/usr/bin/env bash
# cc-watcher.sh — two modes:
#  (A) DEFAULT audit (cron/launchd): scan ALL CC sessions for orphans/stale-locks/
#      longruns. Findings → stdout. `--quiet` = output only on findings.
#  (B) §Phase-2 resident per-session daemon: `--watch <session>` — the ONE deterministic
#      poller. It probes (cc-monitor --force-capture) ONLY when the hook-driven heartbeat
#      goes stale, disambiguating a long think from a freeze (the one thing no hook can
#      see). This moves the monitoring CADENCE off the LLM onto a守时 shell loop.
#      cc-start launches it (nohup) per session; cc-finish --kill-session kills it; it
#      also self-retires when the session dies. `--once` = single check (unit-testable).
#      §R8c③: the resident loop ALSO runs a lightweight ccusage check every
#      CC_USAGE_CHECK_EVERY (default 10) loops — backgrounded, never blocking the freeze
#      probe. On a usage signal (cumulative tokens ≥ CC_USAGE_CEIL, or 'approaching limit'
#      text) it writes /tmp/cc-usage-alert-<session> (Hermes reads passively, like
#      cc-freeze-<s>); below threshold it clears the stale alert. Any ccusage failure →
#      silent degrade (exit 0), alert untouched. `--usage-check` = single sync check (testable).
# Usage: cc-watcher.sh [--quiet]
#        cc-watcher.sh --watch <session> [--once] [--usage-check] [--stale <s>] [--interval <s>]

set -euo pipefail

QUIET=false
WATCH_SESSION="" ONCE=false USAGE_CHECK_NOW=false
STALE="${CC_WATCH_STALE:-45}"        # heartbeat older than this (s) → probe
INTERVAL="${CC_WATCH_INTERVAL:-15}"  # daemon loop sleep (s)
# §R8c③ 顺带用量告警：每 N 圈跑一次轻量 ccusage 检查（避免频繁调）。可配。
USAGE_EVERY="${CC_USAGE_CHECK_EVERY:-10}"   # 每多少圈跑一次用量检查
USAGE_CEIL="${CC_USAGE_CEIL:-1500000000}"   # 累计 token 天花板阈值（默认 1.5B，可配）
CC_USAGE_CMD="${CC_USAGE_CMD:-npx --yes ccusage@latest}"   # 可注入 stub 做 hermetic 测试
USAGE_BOUND="${CC_USAGE_TIMEOUT_S:-30}"     # ccusage 调用上限（s）
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet)        QUIET=true; shift ;;
    --watch)        WATCH_SESSION="$2"; shift 2 ;;
    --once)         ONCE=true; shift ;;
    --usage-check)  USAGE_CHECK_NOW=true; shift ;;  # 单次同步用量检查（unit-testable）
    --stale)        STALE="$2"; shift 2 ;;
    --interval)     INTERVAL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ── Mode B: resident per-session freeze-probe daemon ──────────
if [[ -n "$WATCH_SESSION" ]]; then
  MONITOR="$(cd "$(dirname "$0")" && pwd)/cc-monitor.sh"
  RETIRE=0

  # ── §R8c③ 顺带用量告警 ─────────────────────────────────────────
  # watcher 守护进程顺带轻量查 ccusage 用量信号，发现异常写 /tmp/cc-usage-alert-<s>
  # （Hermes 被动读，同 cc-freeze-<s> 语义）。每 USAGE_EVERY 圈才跑一次（避免频繁调）。
  # 主循环里【后台】跑、绝不阻塞冻结探针的守时节律；任何失败静默降级、不动 alert。
  # 诚实边界：ccusage 只有【累计消耗】，没有【剩余/限额】——故主判据是「累计 token ≥ 天花板」
  # 这个粗粒度跘线，外加对原始输出 best-effort grep 'approaching limit'（ccusage 通常无此字段）。
  # 真实剩余仍须用户敲 /usage（见 references/usage-reporting-pattern.md）。

  # 可移植有界执行（macOS 无 timeout → gtimeout/timeout/纯 bash 三级回退；同 cc-usage.sh）
  run_bounded() {
    local secs="$1"; shift
    if command -v gtimeout >/dev/null 2>&1; then gtimeout "$secs" "$@"; return $?; fi
    if command -v timeout  >/dev/null 2>&1; then timeout  "$secs" "$@"; return $?; fi
    local tmpf pid i=0 rc
    tmpf=$(mktemp)
    "$@" >"$tmpf" 2>/dev/null &
    pid=$!
    while kill -0 "$pid" 2>/dev/null; do
      if [[ "$i" -ge "$secs" ]]; then
        kill -TERM "$pid" 2>/dev/null || true; sleep 1; kill -KILL "$pid" 2>/dev/null || true
        cat "$tmpf"; rm -f "$tmpf"; return 124
      fi
      sleep 1; i=$((i+1))
    done
    wait "$pid" 2>/dev/null; rc=$?
    cat "$tmpf"; rm -f "$tmpf"; return "$rc"
  }

  # usage_check <session> — 跑一次轻量 ccusage 检查；命中→原子写 alert，未命中→清陈旧 alert。
  # 全程降级：ccusage 不可用/超时/非 JSON → 直接 return 0，【不动】既有 alert（不误清、不误写）。
  usage_check() {
    local s="$1"
    local alert="/tmp/cc-usage-alert-${s}" out tok hit="" reason=""
    # shellcheck disable=SC2086  # CC_USAGE_CMD 需词分割（"npx --yes ccusage@latest"）
    out=$(run_bounded "$USAGE_BOUND" $CC_USAGE_CMD --json 2>/dev/null) || return 0
    [[ -z "$out" ]] && return 0
    # 信号①（兜底）：原始输出字面含告警字样（ccusage 累计 JSON 通常无，留作前向兼容）
    if printf '%s' "$out" | grep -Eqi 'approaching[[:space:]]+(your[[:space:]]+)?limit|rate[[:space:]]+limit'; then
      hit=1; reason="ccusage 输出含告警字样（approaching/rate limit）"
    fi
    # 信号②（主判据）：累计 totalTokens ≥ 天花板阈值
    if command -v jq >/dev/null 2>&1; then
      tok=$(printf '%s' "$out" | jq -er '.totals.totalTokens' 2>/dev/null || echo "")
      if [[ "$tok" =~ ^[0-9]+$ ]] && [[ "$tok" -ge "$USAGE_CEIL" ]]; then
        hit=1; reason="累计 ${tok} tokens ≥ 天花板 ${USAGE_CEIL}（敲 /usage 看真实剩余）"
      fi
    fi
    if [[ -n "$hit" ]]; then
      local tmpf="${alert}.tmp.$$"
      if printf '%s | session=%s | %s\n' \
           "$(date -u +%Y-%m-%dT%H:%M:%S)" "$s" "$reason" > "$tmpf" 2>/dev/null; then
        mv -f "$tmpf" "$alert" 2>/dev/null || rm -f "$tmpf" 2>/dev/null
      fi
    else
      # 实测在阈值以下 → 清掉陈旧 alert，避免长期误报
      [[ -f "$alert" ]] && rm -f "$alert" 2>/dev/null
    fi
    return 0
  }

  # 测试入口：单次同步用量检查后退出（CC_USAGE_CMD 注入 stub → 零网络可断言）
  if $USAGE_CHECK_NOW; then
    usage_check "$WATCH_SESSION" || true
    exit 0
  fi
  # One check: retire if the session is gone; else probe only when the heartbeat is
  # stale (hooks stopped touching it → a pure-think gap or a real freeze).
  watch_once() {
    RETIRE=0
    local s="$1"
    if ! tmux has-session -t "$s" 2>/dev/null; then RETIRE=1; return 0; fi
    local hb="/tmp/cc-heartbeat-${s}" age=999999 m
    if [[ -f "$hb" ]]; then
      m=$(stat -f %m "$hb" 2>/dev/null || echo 0)
      age=$(( $(date +%s) - m ))
    fi
    if [[ "$age" -ge "$STALE" ]]; then
      # §P1-1: hook 现在直接写状态权威 /tmp/cc-status-<s>.json。watcher 缩职责——
      # 心跳陈旧时，若 hook 说状态是「静默本属预期」(IDLE 等待输入 / COMPLETED 已完成 /
      # BLOCKED 等权限 / GONE / ERROR)→ 直接信 hook，不抓屏。只有「在途状态却沉默」
      # (RECEIVED/TOOL/ACTIVE/未知/无 status 文件) 才兜底抓屏——这正是 hook 看不见的
      # 纯思考-或-冻结歧义区。注：hook 不会写 THINKING（纯思考无事件），故按状态语义而非
      # 字面 THINKING 判定；skip-list 设计让未知/未来状态默认仍探（保守）。
      local sf="/tmp/cc-status-${s}.json" hstate=""
      if [[ -f "$sf" ]] && command -v jq >/dev/null 2>&1; then
        hstate=$(jq -r '.state // ""' "$sf" 2>/dev/null || echo "")
      fi
      case "$hstate" in
        IDLE|COMPLETED|GONE|BLOCKED|ERROR|COMPACTING) : ;;  # 信 hook，不探
        *) bash "$MONITOR" --session "$s" --force-capture >/dev/null 2>&1 || true ;;
      esac
    fi
    return 0
  }
  if $ONCE; then
    watch_once "$WATCH_SESSION"
    exit 0
  fi
  LOOP=0
  while true; do
    watch_once "$WATCH_SESSION"
    [[ "$RETIRE" -eq 1 ]] && exit 0
    # §R8c③ 每 USAGE_EVERY 圈顺带跑一次用量检查——【后台】跑，不阻塞下一轮冻结探针。
    LOOP=$((LOOP + 1))
    if [[ "$USAGE_EVERY" -gt 0 ]] && [[ $((LOOP % USAGE_EVERY)) -eq 0 ]]; then
      ( usage_check "$WATCH_SESSION" ) >/dev/null 2>&1 &
    fi
    sleep "$INTERVAL"
  done
fi

# ── Mode A: default global audit (unchanged) ─────────────────
FINDINGS=0
NOW=$(date -u +%Y-%m-%dT%H:%M:%S)

TMUX_CC=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^hermes-cc-' || true)
LOCK_DIRS=$(ls -d /tmp/cc-lock-*/ 2>/dev/null || true)

# ── 1. Sessions without locks ─────────────────────────────────
if [[ -n "$TMUX_CC" && -z "$LOCK_DIRS" ]]; then
  while IFS= read -r sess; do
    [[ -z "$sess" ]] && continue
    FINDINGS=$((FINDINGS + 1))
    echo "⚠️  [ORPHAN-SESSION] '$sess' has NO lock dir (bypassed cc-start.sh?)"
  done <<< "$TMUX_CC"
fi

# ── 2. Stale locks (PID dead) ─────────────────────────────────
if [[ -n "$LOCK_DIRS" ]]; then
  for lock in $LOCK_DIRS; do
    [[ -z "$lock" ]] && continue
    LOCK_PID=$(cat "$lock/tmux_pid" 2>/dev/null || cat "$lock/script_pid" 2>/dev/null || echo "?")
    LOCK_SESSION=$(cat "$lock/session" 2>/dev/null || echo "?")
    LOCK_CREATED=$(cat "$lock/created" 2>/dev/null || echo "?")
    if [[ "$LOCK_PID" != "?" ]]; then
      # v1.3: use tmux has-session for STALE detection
      if [[ "$LOCK_SESSION" != "?" ]] && ! tmux has-session -t "$LOCK_SESSION" 2>/dev/null; then
        FINDINGS=$((FINDINGS + 1))
        echo "⚠️  [STALE-LOCK] '$(basename "$lock")' session '$LOCK_SESSION' gone (created $LOCK_CREATED)"
      elif ! kill -0 "$LOCK_PID" 2>/dev/null; then
        FINDINGS=$((FINDINGS + 1))
        echo "⚠️  [STALE-LOCK] '$(basename "$lock")' PID $LOCK_PID dead (created $LOCK_CREATED)"
      fi
    fi
  done
fi

# ── 3. Long-running sessions (>6 hours) ───────────────────────
if [[ -n "$TMUX_CC" ]]; then
  while IFS= read -r sess; do
    [[ -z "$sess" ]] && continue
    CREATED_TS=$(tmux display-message -t "$sess" -p '#{session_created}' 2>/dev/null || echo 0)
    if [[ "$CREATED_TS" != "0" ]]; then
      AGE=$(( $(date +%s) - CREATED_TS ))
      if [[ $AGE -gt 21600 ]]; then
        HOURS=$((AGE / 3600))
        FINDINGS=$((FINDINGS + 1))
        echo "⚠️  [LONGRUN] '$sess' running ${HOURS}h (abandoned?)"
      fi
    fi
  done <<< "$TMUX_CC"
fi

# ── Output ────────────────────────────────────────────────────
if $QUIET; then
  [[ $FINDINGS -gt 0 ]] && echo "[cc-watcher] $FINDINGS finding(s) at $NOW"
else
  SESS_COUNT=$( [[ -z "$TMUX_CC" ]] && echo 0 || { echo "$TMUX_CC" | grep -c 'hermes-cc-' 2>/dev/null || echo 0; } )
  LOCK_COUNT=$( [[ -z "$LOCK_DIRS" ]] && echo 0 || { echo "$LOCK_DIRS" | grep -c 'cc-lock-' 2>/dev/null || echo 0; } )
  echo "cc-watcher @ $NOW | sessions=$SESS_COUNT locks=$LOCK_COUNT findings=$FINDINGS"
  [[ $FINDINGS -eq 0 ]] && echo "✅ All clear"
fi

exit 0
