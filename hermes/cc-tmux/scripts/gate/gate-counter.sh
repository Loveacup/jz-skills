#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# gate-counter.sh —— 终止计数器 gate
#
# 【基质无关】 不依赖 tmux / cc-tmux 运行时；纯参数进、退出码出。
# 【零 tmux 耦合】不读 tmux pane；状态仅落 /tmp 计数文件，任何基质可调。
# 【提升条件】 当前唯一消费者 cc-tmux，暂居 cc-tmux/scripts/gate/；
#              出现第 2 消费者 → 整组 gate-*.sh 提升为独立 audit skill（裁决③ 复活）。
#
# 职责：对「讨论轮/退回轮」做原子持久硬计数；达上限返回特定退出码，强制升级。
#       agent 无法乐观绕过（数字落盘，不在对话上下文里）。
#
# 参数：
#   --key <标识>          计数器标识（通常 = session 名）
#   --kind discuss|reject 两类独立计数
#   --inc | --get | --reset   三选一动作（默认 --get）
#   --limit <N>           上限（discuss 默认 3 / reject 默认 2）
#   --json                JSON 输出
#   -h|--help             打印本头注
#
# 退出码： 0 成功且未达上限 · 20 自增后达到/超过上限（停循环、升级人工）· 3 参数错误
# stdout： {key, kind, count, limit, over}
# 存储：  /tmp/cc-counter-<key>.json（写临时文件再 mv——仅防撕裂读，不防并发 RMW 丢更新；
#         当前 cc-tmux 串行调用故无碍；后续若并发复用，须补 mkdir 锁或 flock）
#         清理：由调用方收尾负责 —— cc-tmux 下即 cc-finish.sh 随状态文件一并清。
#
# 示例：
#   bash gate-counter.sh --key sess-A --kind reject --inc --limit 2
#   # exit 0 → 可继续退回 CC；exit 20 → 退回达 2 次，停循环、升级人工（SOUL「退回 ≤2」）
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

KEY=""; KIND=""; ACTION="get"; LIMIT=""; JSON=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --key)    KEY="$2"; shift 2 ;;
    --kind)   KIND="$2"; shift 2 ;;
    --inc)    ACTION="inc"; shift ;;
    --get)    ACTION="get"; shift ;;
    --reset)  ACTION="reset"; shift ;;
    --limit)  LIMIT="$2"; shift 2 ;;
    --json)   JSON=1; shift ;;
    -h|--help) sed -n '2,34p' "$0"; exit 0 ;;
    *) echo "gate-counter: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ -z "$KEY" ]] && { echo "gate-counter: 缺 --key" >&2; exit 3; }
case "$KIND" in
  discuss) : "${LIMIT:=3}" ;;
  reject)  : "${LIMIT:=2}" ;;
  *) echo "gate-counter: --kind 须 discuss|reject" >&2; exit 3 ;;
esac

FILE="/tmp/cc-counter-${KEY}.json"
read_kind() {  # 读某 kind 当前值，缺则 0
  [[ -f "$FILE" ]] || { echo 0; return; }
  local n; n=$(grep -oE "\"$1\":[0-9]+" "$FILE" 2>/dev/null | grep -oE '[0-9]+' || true)
  echo "${n:-0}"
}

cur=$(read_kind "$KIND")
case "$ACTION" in
  reset) cur=0 ;;
  inc)   cur=$((cur + 1)) ;;
  get)   : ;;
esac

# 原子写：两个 kind 同存一文件，写 tmp 再 mv（同分区 mv 原子）
if [[ "$ACTION" != "get" ]]; then
  other_kind=$([[ "$KIND" == discuss ]] && echo reject || echo discuss)
  other=$(read_kind "$other_kind")
  tmp="${FILE}.$$"
  printf '{"key":"%s","%s":%d,"%s":%d}\n' "$KEY" "$KIND" "$cur" "$other_kind" "$other" > "$tmp"
  mv -f "$tmp" "$FILE"
fi

over=false; ec=0
if [[ "$ACTION" == "inc" && $cur -ge $LIMIT ]]; then over=true; ec=20; fi

if [[ $JSON -eq 1 ]]; then
  printf '{"key":"%s","kind":"%s","count":%d,"limit":%d,"over":%s}\n' "$KEY" "$KIND" "$cur" "$LIMIT" "$over"
else
  echo "key=$KEY kind=$KIND count=$cur limit=$LIMIT over=$over"
fi
exit $ec
