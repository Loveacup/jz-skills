#!/usr/bin/env bash
# cc-send-robust.sh — 底层 send-keys 原语库（轨1 P0-1）
#
# 根治痛点②(Pitfall #5/#18)：send-keys 从「赌 Enter 能生效」升级为
# 「发完回读校验 + 失败重试」。本文件是渐进替换的第一步——只提供原语库，
# 不改 cc-send.sh 本体；后续 cc-send.sh 可逐步改为调用这里的函数。
#
# 成功判据按 CC 现实（**不是** primeline 的「pane 里看到 message = 成功」）：
#   capture pane 底部，分类——
#     · "Press up to edit queued"   → queue 模式：Escape 退出后重发整条 (rc 2)
#     · ❯ 后有残留文本               → Enter 未生效：补发 Enter         (rc 1)
#     · 空 ❯ 或根本无 ❯ (CC 已 busy) → 已消费 = 成功                    (rc 0)
#   与 cc-send.sh §3.2 verify_delivered 同源同口径，便于后续接线。
#   重试有界，耗尽返回非 0（不静默假成功，per plan §3.2 / L1 表）。
#
# 用法 A（source 取函数）:
#   source /path/to/cc-send-robust.sh
#   send_to_pane    <target> <message> [max_retries=3]   # 单行 + 校验 + 重试
#   send_multiline  <target> <text>    [max_retries=3]   # 多行 load/paste-buffer
#   send_clear_then <target> <message> [max_retries=3]   # C-u 清行 + send_to_pane
# 用法 B（CLI 独立调用）:
#   cc-send-robust.sh send-to-pane    <target> <message> [max_retries]
#   cc-send-robust.sh send-multiline  <target> <text>    [max_retries]
#   cc-send-robust.sh send-clear-then <target> <message> [max_retries]
#
# 返回码：0 成功 · 1 重试耗尽（仍未消费）· 3 tmux 投递失败（如 target 不存在）

# ── 可调时序（测试可用环境变量覆盖以加速；默认值为生产用值）──
: "${CC_SEND_T_LITERAL:=0.5}"   # 字面注入 → Enter 之间（防输入缓冲竞态）
: "${CC_SEND_T_VERIFY:=1.0}"    # Enter/动作 → 回读校验 之间（等 CC 渲染）
: "${CC_SEND_T_ESCAPE:=0.3}"    # Escape → 重发 之间
: "${CC_SEND_T_PASTE:=0.5}"     # paste-buffer → Enter 之间

# 去除 ANSI 转义序列（capture-pane -p 通常已无 ESC，作防御性净化）
strip_ansi() {
  sed $'s/\x1b\\[[0-9;?]*[a-zA-Z]//g' 2>/dev/null || cat
}

# 读 pane 底部有效内容（去空行，取末 4 行），与 cc-send.sh 同口径
_capture_tail() {
  local target="$1"
  tmux capture-pane -t "$target" -p -S -6 2>/dev/null \
    | strip_ansi | grep -v '^[[:space:]]*$' | tail -4 || true
}

# 分类 pane 状态（仅用返回码传递）：
#   0 = consumed(成功)   1 = residual(Enter 未生效)   2 = queue 模式
_classify_pane() {
  local target="$1" tail4 pl c
  tail4=$(_capture_tail "$target")
  if printf '%s' "$tail4" | grep -q 'Press up to edit queued'; then
    return 2
  fi
  pl=$(printf '%s' "$tail4" | grep '❯' | tail -1 || true)
  if [[ -n "$pl" ]]; then
    c=$(printf '%s' "$pl" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//')
    [[ -n "$c" ]] && return 1
  fi
  return 0
}

# 修复一次卡住状态：rc=2 → Escape + 重发整条；rc=1 → 仅补发 Enter
_repair_singleline() {
  local target="$1" message="$2" rc="$3"
  if [[ "$rc" -eq 2 ]]; then
    tmux send-keys -t "$target" Escape 2>/dev/null || true
    sleep "$CC_SEND_T_ESCAPE"
    tmux send-keys -t "$target" -l "$message" 2>/dev/null || true
    sleep "$CC_SEND_T_LITERAL"
    tmux send-keys -t "$target" Enter 2>/dev/null || true
  else
    tmux send-keys -t "$target" Enter 2>/dev/null || true
  fi
}

# 单行发送 + 回读校验(CC 现实) + 有界重试
send_to_pane() {
  local target="$1" message="$2" max_retries="${3:-3}"
  local attempt=0 rc

  # -l = literal，防 #/! 等被 tmux 解释；Enter 单独发，防输入缓冲竞态
  tmux send-keys -t "$target" -l "$message" 2>/dev/null || return 3
  sleep "$CC_SEND_T_LITERAL"
  tmux send-keys -t "$target" Enter 2>/dev/null || return 3
  sleep "$CC_SEND_T_VERIFY"

  while :; do
    rc=0; _classify_pane "$target" || rc=$?
    if [[ "$rc" -eq 0 ]]; then
      return 0
    fi
    if (( attempt >= max_retries )); then
      return 1
    fi
    attempt=$(( attempt + 1 ))
    _repair_singleline "$target" "$message" "$rc"
    sleep "$CC_SEND_T_VERIFY"
  done
}

# 多行发送：load-buffer + paste-buffer（防多行被逐行触发），同样回读校验 + 重试
send_multiline() {
  local target="$1" text="$2" max_retries="${3:-3}"
  local buf="cc-tmux-mlbuf-$$" attempt=0 rc result=1

  printf '%s' "$text" | tmux load-buffer -b "$buf" - 2>/dev/null || return 3
  # 不带 -d：保留 buffer 以便 queue 重试时重新 paste；函数末尾统一 delete
  tmux paste-buffer -p -b "$buf" -t "$target" 2>/dev/null \
    || { tmux delete-buffer -b "$buf" 2>/dev/null; return 3; }
  sleep "$CC_SEND_T_PASTE"
  tmux send-keys -t "$target" Enter 2>/dev/null || true
  sleep "$CC_SEND_T_VERIFY"

  while :; do
    rc=0; _classify_pane "$target" || rc=$?
    if [[ "$rc" -eq 0 ]]; then result=0; break; fi
    if (( attempt >= max_retries )); then result=1; break; fi
    attempt=$(( attempt + 1 ))
    if [[ "$rc" -eq 2 ]]; then
      tmux send-keys -t "$target" Escape 2>/dev/null || true
      sleep "$CC_SEND_T_ESCAPE"
      tmux paste-buffer -p -b "$buf" -t "$target" 2>/dev/null || true
      sleep "$CC_SEND_T_PASTE"
      tmux send-keys -t "$target" Enter 2>/dev/null || true
    else
      tmux send-keys -t "$target" Enter 2>/dev/null || true
    fi
    sleep "$CC_SEND_T_VERIFY"
  done

  tmux delete-buffer -b "$buf" 2>/dev/null || true
  return "$result"
}

# C-u 清当前行残留 + send_to_pane（收尾用，防上一次残留干扰本次输入）
send_clear_then() {
  local target="$1" message="$2" max_retries="${3:-3}"
  tmux send-keys -t "$target" C-u 2>/dev/null || return 3
  sleep "$CC_SEND_T_ESCAPE"
  send_to_pane "$target" "$message" "$max_retries"
}

# ── 被直接执行时：CLI dispatch（可独立调用）。被 source 时只定义函数 ──
if [[ "${BASH_SOURCE[0]:-$0}" == "${0}" ]]; then
  set -uo pipefail   # 不开 -e：函数依赖非零返回控制流
  cmd="${1:-}"; [[ $# -gt 0 ]] && shift
  case "$cmd" in
    send-to-pane)    send_to_pane "$@" ;;
    send-multiline)  send_multiline "$@" ;;
    send-clear-then) send_clear_then "$@" ;;
    *)
      echo "Usage: cc-send-robust.sh {send-to-pane|send-multiline|send-clear-then} <target> <payload> [max_retries]" >&2
      exit 1 ;;
  esac
  exit $?
fi
