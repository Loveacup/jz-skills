#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# gate-counter.sh —— 轮次 / reject 硬计数 gate
#
# 【基质无关】 不依赖 Hermes / omp；状态仅落 /tmp 计数文件，自包含。
#
# 职责：对「执行轮次」「reject 次数」做原子持久硬计数；超上限返回 exit 20，强制升级人工。
#       数字落盘（不在对话上下文里），agent 无法乐观绕过——这是「硬终止」红线的牙齿。
#
# 终止条件（执行包契约）：round_count > 3  或  reject_count > 2
#   → 即第 4 轮、第 3 次 reject 触发。（注意：是 `>` 不是 `>=`，故 round=3/reject=2 仍放行。）
#
# 参数：
#   --task-id <id>（或 --key <id>）  计数器标识（必填）
#   --inc-round | --inc-reject | --check   动作（默认 --check，只读判断）
#   --round-limit <N>   round 上限（默认 3）
#   --reject-limit <N>  reject 上限（默认 2）
#   --json              （默认即 JSON 输出）
#   -h|--help           打印本头注
#
# 退出码： 0 在限内 · 20 硬终止（超限，停循环、升级人工，不可绕过）· 3 参数错误
# stdout： {"task_id","round_count","reject_count","round_limit","reject_limit","terminated"}
# 存储：  ${OMP_TMPDIR:-/tmp}/omp-counter-<task_id>.json（写 tmp 再 mv，防撕裂读；
#         串行调用安全；清理由 omp-finish.sh / omp-gc.sh 负责）
#
# 示例：
#   bash gate-counter.sh --task-id t1 --inc-round    # 第 4 次调用 → exit 20
#   bash gate-counter.sh --task-id t1 --inc-reject   # 第 3 次调用 → exit 20
#   bash gate-counter.sh --task-id t1 --check        # 只读当前计数 + 是否已超限
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

OMP_TMPDIR="${OMP_TMPDIR:-/tmp}"
TASK_ID=""; ACTION="check"; RL=3; JL=2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-id|--key) TASK_ID="$2"; shift 2 ;;
    --inc-round)     ACTION="inc-round"; shift ;;
    --inc-reject)    ACTION="inc-reject"; shift ;;
    --check)         ACTION="check"; shift ;;
    --round-limit)   RL="$2"; shift 2 ;;
    --reject-limit)  JL="$2"; shift 2 ;;
    --json)          shift ;;
    -h|--help)       sed -n '2,37p' "$0"; exit 0 ;;
    *) echo "gate-counter: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ -n "$TASK_ID" ]] || { echo "gate-counter: 缺 --task-id" >&2; exit 3; }
[[ ${#TASK_ID} -le 128 && "$TASK_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "gate-counter: 非法 task_id" >&2; exit 3; }
[[ "$RL" =~ ^[0-9]+$ && "$JL" =~ ^[0-9]+$ ]] || { echo "gate-counter: limit 须为非负整数" >&2; exit 3; }

FILE="$OMP_TMPDIR/omp-counter-${TASK_ID}.json"

# ── 读当前计数（缺/坏 → 0）──
rc=0; jc=0
if [[ -f "$FILE" ]]; then
  rc=$(jq -r '.round_count  // 0' "$FILE" 2>/dev/null || echo 0)
  jc=$(jq -r '.reject_count // 0' "$FILE" 2>/dev/null || echo 0)
fi
[[ "$rc" =~ ^[0-9]+$ ]] || rc=0
[[ "$jc" =~ ^[0-9]+$ ]] || jc=0

# ── 应用动作 ──
case "$ACTION" in
  inc-round)  rc=$((rc + 1)) ;;
  inc-reject) jc=$((jc + 1)) ;;
  check)      : ;;
esac

# ── 原子写（仅自增时落盘）──
if [[ "$ACTION" != "check" ]]; then
  tmp="${FILE}.$$"
  jq -nc --arg id "$TASK_ID" --argjson rc "$rc" --argjson jc "$jc" \
         --argjson rl "$RL" --argjson jl "$JL" \
    '{task_id:$id,round_count:$rc,reject_count:$jc,round_limit:$rl,reject_limit:$jl}' > "$tmp"
  mv -f "$tmp" "$FILE"
fi

# ── 裁决：count > limit → 硬终止 ──
terminated=false; ec=0
if [[ "$rc" -gt "$RL" || "$jc" -gt "$JL" ]]; then terminated=true; ec=20; fi

printf '{"task_id":"%s","round_count":%d,"reject_count":%d,"round_limit":%d,"reject_limit":%d,"terminated":%s}\n' \
  "$TASK_ID" "$rc" "$jc" "$RL" "$JL" "$terminated"
exit $ec
