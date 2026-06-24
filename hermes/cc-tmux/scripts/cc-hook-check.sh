#!/usr/bin/env bash
# cc-hook-check.sh — CC hook 冒烟自检（替代 cc-hook-bug-registry.md 的人工月度复查）
#
# 背景：hook 正确性原靠「人工每月复查」——违背 design-principles「LLM/人不擅长定时重复义务」。
#       本脚本把该义务搬到 cron（每月 1 号自动跑，结果走 cron deliver 回报）。安装见
#       references/cc-hook-cron-monthly.md。
#
# 职责：对【当前活跃】的 cc-tmux 驱动 CC session，【被动检视】hook 产物是否如期落盘——
#       不主动驱动一轮真 CC（不打扰运行中的任务）。检视三类 hook 产物：
#         · cc-status-<s>.json  ← cc-status-writer（接 8 事件：PreToolUse/PostToolUse/
#                                  UserPromptSubmit/Notification/SessionStart/SessionEnd/
#                                  Stop/PreCompact）原子写。有效 = 整条 hook 链在触发。
#         · cc-heartbeat-<s>    ← PreToolUse 等热心跳 touch。存在 = 心跳 hook 在烧。
#         · cc-state-<s>.log    ← UserPromptSubmit/Notification 生命周期日志（信息项）。
#         · cc-turn-done-<s>    ← Stop 写的完成标记（信息项，mid-turn 时本就不在）。
#         · SessionStart context 注入 ← capture-pane best-effort grep（信息项，scrollback 可能已滚走）。
#
# 自身不依赖活 CC session：无活跃 session → 打印 "(no active CC sessions)" 且 exit 0。
#
# 退出码： 0 = 无活跃 session 或全部核心信号健康 · 1 = ≥1 session 核心信号缺失（疑似 hook 回归）
#          · 2 = 参数错误
#
# 可移植/可测（注入 → 零真实 session/网络）：
#   CC_HOOK_CHECK_TMUX     tmux 调用（默认 "tmux"）——测试注入 stub 列 session + capture-pane
#   CC_HOOK_CHECK_TMPDIR   产物基目录（默认 "/tmp"）——cc-status/heartbeat/state/turn-done 都在此下
#   CC_HOOK_CHECK_FRESH_S  心跳「新鲜」窗口（默认 7200s/2h）；陈旧只 WARN（idle session 属正常），不判 FAIL
#
# 机器断言行（stderr）：
#   HOOKCHECK total=.. healthy=.. degraded=..
#   HOOKITEM session=.. status=.. heartbeat=.. hb_age=.. statelog=.. turndone=.. context=.. verdict=ok|degraded

set -euo pipefail

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) sed -n '2,33p' "$0"; exit 0 ;;
    *) echo "❌ cc-hook-check: unknown arg: $1" >&2; exit 2 ;;
  esac
done

TMUX="${CC_HOOK_CHECK_TMUX:-tmux}"
TMP="${CC_HOOK_CHECK_TMPDIR:-/tmp}"
FRESH_S="${CC_HOOK_CHECK_FRESH_S:-7200}"
NOW=$(date +%s)
ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# shellcheck disable=SC2086  # CC_HOOK_CHECK_TMUX 需词分割（"bash stub.sh"）
tmuxc() { $TMUX "$@"; }

# ── 枚举活跃 cc-tmux 驱动 session（命名前缀 hermes-cc-）──────────────
SESSIONS=$(tmuxc list-sessions -F '#{session_name}' 2>/dev/null | grep '^hermes-cc-' || true)

if [[ -z "$SESSIONS" ]]; then
  echo "HOOKCHECK total=0 healthy=0 degraded=0" >&2
  echo "🪝 cc-hook 冒烟自检 @ $ISO"
  echo "  (no active CC sessions)"
  exit 0
fi

TOTAL=0 HEALTHY=0 DEGRADED=0
REPORT=()

for s in $SESSIONS; do
  [[ -z "$s" ]] && continue
  TOTAL=$((TOTAL + 1))

  status_f="${TMP}/cc-status-${s}.json"
  hb_f="${TMP}/cc-heartbeat-${s}"
  log_f="${TMP}/cc-state-${s}.log"
  done_f="${TMP}/cc-turn-done-${s}"

  # 核心①：cc-status-<s>.json 存在、有效 JSON、含 .state 且 .seq≥1（证 writer 接的 8 事件在触发）
  status_v="missing"
  if [[ -f "$status_f" ]] && command -v jq >/dev/null 2>&1; then
    st=$(jq -r '.state // empty' "$status_f" 2>/dev/null || echo "")
    sq=$(jq -r '.seq // 0'       "$status_f" 2>/dev/null || echo 0)
    [[ "$sq" =~ ^[0-9]+$ ]] || sq=0
    if [[ -n "$st" && "$sq" -ge 1 ]]; then status_v="ok(state=$st,seq=$sq)"; else status_v="invalid"; fi
  elif [[ -f "$status_f" ]]; then
    status_v="present(jq-absent)"   # 文件在但无 jq 验不了内容 → 不当 FAIL
  fi

  # 核心②：cc-heartbeat-<s> 存在（证热心跳 hook 在烧）；附心跳年龄（陈旧只 WARN）
  hb_v="missing"; hb_age="-"
  if [[ -f "$hb_f" ]]; then
    m=$(stat -f %m "$hb_f" 2>/dev/null || echo 0)
    hb_age=$(( NOW - m ))
    if [[ "$hb_age" -le "$FRESH_S" ]]; then hb_v="fresh"; else hb_v="stale"; fi
  fi

  # 信息项：state-log 行数 / turn-done 是否在 / context 注入痕迹（best-effort）
  log_lines=0; [[ -f "$log_f" ]] && log_lines=$(grep -c '' "$log_f" 2>/dev/null || echo 0)
  turndone="no"; [[ -f "$done_f" ]] && turndone="yes"
  context="unknown"
  pane=$(tmuxc capture-pane -t "$s" -p -S - 2>/dev/null || echo "")
  if [[ -n "$pane" ]]; then
    if printf '%s' "$pane" | grep -q '\[cc-tmux\] 你是被 cc-tmux 驱动的 CC'; then
      context="injected"
    else
      context="not-in-scrollback"   # 可能已滚出 buffer，非确定性失败
    fi
  fi

  # 判定：核心①②任一硬缺失 → degraded（疑似 hook 回归）
  verdict="ok"
  if [[ "$status_v" == "missing" || "$status_v" == "invalid" || "$hb_v" == "missing" ]]; then
    verdict="degraded"
  fi
  if [[ "$verdict" == "ok" ]]; then HEALTHY=$((HEALTHY + 1)); else DEGRADED=$((DEGRADED + 1)); fi

  echo "HOOKITEM session=$s status=$status_v heartbeat=$hb_v hb_age=${hb_age}s statelog=$log_lines turndone=$turndone context=$context verdict=$verdict" >&2

  icon="✅"; [[ "$verdict" == "degraded" ]] && icon="❌"
  REPORT+=("$icon $s")
  REPORT+=("     status:    $status_v")
  REPORT+=("     heartbeat: $hb_v (age ${hb_age}s)")
  REPORT+=("     state-log: ${log_lines} line(s) · turn-done: $turndone · context: $context")
done

echo "HOOKCHECK total=$TOTAL healthy=$HEALTHY degraded=$DEGRADED" >&2

echo "🪝 cc-hook 冒烟自检 @ $ISO"
echo "  sessions=$TOTAL · healthy=$HEALTHY · degraded=$DEGRADED"
printf '%s\n' "${REPORT[@]}"
if [[ "$DEGRADED" -gt 0 ]]; then
  echo ""
  echo "  ⚠️ $DEGRADED session(s) 核心 hook 产物缺失/失效 → 疑似 hook 回归。"
  echo "     复查 references/cc-hook-bug-registry.md，核对 CC 版本是否升级、settings.runtime.json 接线是否完好。"
  exit 1
fi
echo "  ✅ 全部活跃 session 的核心 hook 产物健康。"
exit 0
