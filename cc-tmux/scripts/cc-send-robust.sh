#!/usr/bin/env bash
# cc-send-robust.sh — 底层 send-keys 原语库（轨1 P0-1）
#
# 根治痛点②(Pitfall #5/#18/#31)：send-keys 从「赌 Enter 能生效」升级为
# 「发完回读校验 + 失败重试 + 未知文本不自动 Enter」。
#
# v1.40.0: 收紧 repair 窗口，仅对刚发送且匹配的消息自动 repair；
#          未知/预测/stale prompt text 一律不自动 Enter → rc 4。
#
# 成功判据按 CC 现实（**不是** primeline 的「pane 里看到 message = 成功」）：
#   capture pane 底部，分类——
#     · "Press up to edit queued"   → queue 模式 (rc 2)
#     · ❯ 后有残留文本 == message   → Enter 未生效 (rc 1)，窗口内可 repair
#     · ❯ 后有残留文本 != message   → 未知/预测/stale (rc 4)，禁止自动 Enter
#     · 空 ❯ 或根本无 ❯ (CC 已 busy) → 已消费 = 成功 (rc 0)
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
# 返回码：
#   0 = delivered/consumed
#   1 = delivery_unconfirmed（允许的 repair 已做但仍未消费）
#   2 = usage_error
#   3 = tmux_delivery_failure（target 不存在或 tmux send/paste 失败）
#   4 = unsafe_prompt_text_refused（未知/预测/stale prompt text，未自动 Enter）

# ── 可调时序（测试可用环境变量覆盖以加速；默认值为生产用值）──
: "${CC_SEND_T_LITERAL:=0.5}"   # 字面注入 → Enter 之间（防输入缓冲竞态）
: "${CC_SEND_T_VERIFY:=1.0}"    # Enter/动作 → 回读校验 之间（等 CC 渲染）
: "${CC_SEND_T_ESCAPE:=0.3}"    # Escape → 重发 之间
: "${CC_SEND_T_PASTE:=0.5}"     # paste-buffer → Enter 之间
: "${CC_SEND_REPAIR_WINDOW_S:=3}"  # v1.40: 仅发送后此窗口内允许自动 repair（0 禁用）
: "${CC_SEND_ALLOW_UNKNOWN_ENTER:=0}"  # v1.40: 仅测试/人工时设 1；生产永远 0
: "${CC_SEND_DEBUG_SIGNALS:=0}"  # v1.40: 设 1 时 stderr 输出分类信号（测试用）

# 去除 ANSI 转义序列（capture-pane -p 通常已无 ESC，作防御性净化）
strip_ansi() {
  sed $'s/\x1b\\[[0-9;?]*[a-zA-Z]//g' 2>/dev/null || cat
}

# 规范化消息文本用于匹配比较（去除首尾空格、压缩连续空格）
_normalize_msg() {
  printf '%s' "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//; s/[[:space:]][[:space:]]*/ /g'
}

# 读 pane 底部有效内容（去空行，取末 4 行），与 cc-send.sh 同口径
_capture_tail() {
  local target="$1"
  tmux capture-pane -t "$target" -p -S -6 2>/dev/null \
    | strip_ansi | grep -v '^[[:space:]]*$' | tail -4 || true
}

# 获取 ❯ 后的文本内容（空 = idle empty）
_prompt_text() {
  local tail4="$1" pl
  pl=$(printf '%s' "$tail4" | grep '❯' | tail -1 || true)
  if [[ -n "$pl" ]]; then
    printf '%s' "$pl" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//'
  fi
}

# 分类 pane 状态并提取 prompt text（通过变量 PT_TEXT / PT_SIGNAL 返回）：
#   0 = consumed(成功)  PT_SIGNAL=consumed
#   1 = residual(Enter 未生效, 文本匹配刚发消息)  PT_SIGNAL=prompt_text_fresh_sent_line
#   2 = queue 模式      PT_SIGNAL=queue_banner
#   4 = unspecified prompt text (未知/预测/stale) PT_SIGNAL=prompt_text_unspecified
_classify_pane() {
  local target="$1" sent_msg="$2" tail4 pt
  PT_TEXT=""; PT_SIGNAL=""
  tail4=$(_capture_tail "$target")
  if printf '%s' "$tail4" | grep -q 'Press up to edit queued'; then
    PT_SIGNAL="queue_banner"; return 2
  fi
  pt=$(_prompt_text "$tail4")
  if [[ -z "$pt" ]]; then
    PT_SIGNAL="prompt_empty_or_busy"; return 0
  fi
  PT_TEXT="$pt"
  # 文本匹配刚发送消息（normalized 比较）→ Enter 未生效
  if [[ -n "$sent_msg" ]] && [[ "$(_normalize_msg "$pt")" == "$(_normalize_msg "$sent_msg")" ]]; then
    PT_SIGNAL="prompt_text_fresh_sent_line"; return 1
  fi
  # 文本不匹配（未知/预测/stale）→ 不安全
  PT_SIGNAL="prompt_text_unspecified"; return 4
}

# 修复一次卡住状态：仅对 fresh_sent_line / queue+matching 做安全 repair
_repair_singleline() {
  local target="$1" message="$2" signal="$3"
  if [[ "$signal" == "queue_banner" ]]; then
    tmux send-keys -t "$target" Escape 2>/dev/null || true
    sleep "$CC_SEND_T_ESCAPE"
    tmux send-keys -t "$target" -l "$message" 2>/dev/null || true
    sleep "$CC_SEND_T_LITERAL"
    tmux send-keys -t "$target" Enter 2>/dev/null || true
  elif [[ "$signal" == "prompt_text_fresh_sent_line" ]]; then
    tmux send-keys -t "$target" Enter 2>/dev/null || true
  fi
  # prompt_text_unspecified → 不做任何 repair
}

_debug_signal() {
  [[ "${CC_SEND_DEBUG_SIGNALS:-0}" == "1" ]] || return 0
  echo "SIGNAL session=${1:-?} signal=${2:-?} rc=${3:-?}" >&2
}

# 单行发送 + 回读校验(CC 现实) + 有界重试 + 未知文本防护
send_to_pane() {
  local target="$1" message="$2" max_retries="${3:-3}"
  local attempt=0 rc send_ts now elapsed signal_name

  # -l = literal，防 #/! 等被 tmux 解释；Enter 单独发，防输入缓冲竞态
  tmux send-keys -t "$target" -l "$message" 2>/dev/null || return 3
  sleep "$CC_SEND_T_LITERAL"
  tmux send-keys -t "$target" Enter 2>/dev/null || return 3
  sleep "$CC_SEND_T_VERIFY"
  send_ts=$(date +%s)

  while :; do
    rc=0; _classify_pane "$target" "$message" || rc=$?
    signal_name="${PT_SIGNAL:-unknown}"
    _debug_signal "$target" "$signal_name" "$rc"

    case "$rc" in
      0) return 0 ;;  # consumed 或 busy
      4) return 4 ;;  # v1.40: 未知/预测/stale prompt text → 立即拒绝，不重试
      2|1) ;;          # queue 或 fresh_sent_line → 允许 bounded repair
      *) return 1 ;;   # 意外 rc
    esac

    [[ "${CC_SEND_ALLOW_UNKNOWN_ENTER:-0}" == "1" ]] && {
      _repair_singleline "$target" "$message" "$signal_name"
      sleep "$CC_SEND_T_VERIFY"
      continue
    }

    # 检查 repair window
    now=$(date +%s); elapsed=$(( now - send_ts ))
    if [[ "${CC_SEND_REPAIR_WINDOW_S:-0}" -ne 0 ]] && [[ "$elapsed" -gt "${CC_SEND_REPAIR_WINDOW_S:-3}" ]]; then
      _debug_signal "$target" "repair_window_expired" "$rc"
      return 4  # 窗口过期，不再 repair
    fi

    if (( attempt >= max_retries )); then
      return 1
    fi
    attempt=$(( attempt + 1 ))
    _repair_singleline "$target" "$message" "$signal_name"
    sleep "$CC_SEND_T_VERIFY"
  done
}

# 多行发送：load-buffer + paste-buffer（防多行被逐行触发），同样回读校验 + 重试
# v1.40: 增加未知文本防护
send_multiline() {
  local target="$1" text="$2" max_retries="${3:-3}"
  local buf="cc-tmux-mlbuf-$$" attempt=0 rc result=1

  printf '%s' "$text" | tmux load-buffer -b "$buf" - 2>/dev/null || return 3
  tmux paste-buffer -p -b "$buf" -t "$target" 2>/dev/null \
    || { tmux delete-buffer -b "$buf" 2>/dev/null; return 3; }
  sleep "$CC_SEND_T_PASTE"
  tmux send-keys -t "$target" Enter 2>/dev/null || true
  sleep "$CC_SEND_T_VERIFY"

  while :; do
    rc=0; _classify_pane "$target" "" || rc=$?  # multiline 不匹配具体文本
    _debug_signal "$target" "${PT_SIGNAL:-unknown}" "$rc"
    case "$rc" in
      0) result=0; break ;;
      4) result=4; break ;;  # v1.40: 未知 prompt text → 拒绝
      2|1) ;;
      *) result=1; break ;;
    esac
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
  set -uo pipefail
  cmd="${1:-}"; [[ $# -gt 0 ]] && shift
  case "$cmd" in
    send-to-pane)    send_to_pane "$@" ;;
    send-multiline)  send_multiline "$@" ;;
    send-clear-then) send_clear_then "$@" ;;
    *)
      echo "Usage: cc-send-robust.sh {send-to-pane|send-multiline|send-clear-then} <target> <payload> [max_retries]" >&2
      exit 2 ;;  # v1.40: usage error → rc 2
  esac
  exit $?
fi
