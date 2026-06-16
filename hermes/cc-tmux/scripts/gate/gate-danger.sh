#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# gate-danger.sh —— 危险操作拦截 gate
#
# 【基质无关】 不依赖 tmux / cc-tmux 运行时；纯参数进、退出码出。
# 【零 tmux 耦合】不读 tmux pane、不碰 cc-* 状态文件；任何 agent/编排基质可直接调。
# 【提升条件】 当前唯一消费者 cc-tmux，暂居 cc-tmux/scripts/gate/；
#              出现第 2 消费者 → 整组 gate-*.sh 提升为独立 audit skill（裁决③ 复活）。
#
# 职责：扫描文本/文件中的危险模式（删除/对外发布/改核心配置/提权）。命中 = 人工红线，停。
#
# 参数：
#   --scan-text "<文本>"   直接扫描文本
#   --scan-file <路径>     扫描文件内容（diff / 委派包 / 命令）
#   --patterns-file <路径> 自定义模式（每行一条 ERE），覆盖内置默认
#   --strict               命中即退出、不汇总
#   --json                 JSON 输出
#   -h|--help              打印本头注
#
# 退出码： 0 无危险 · 10 命中（须人工红线，不可自动放行）· 3 参数错误
# stdout： 命中列表 {pattern, line, hit}（单行，便于转发）
#
# 示例：
#   bash gate-danger.sh --scan-file /tmp/cc-proposed-diff.txt
#   # exit 10 → 停，原样转发命中列表给人工，等确认（SOUL「危险类永远人工」）
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

SCAN_TEXT=""; SCAN_FILE=""; PATTERNS_FILE=""; STRICT=0; JSON=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scan-text)     SCAN_TEXT="$2"; shift 2 ;;
    --scan-file)     SCAN_FILE="$2"; shift 2 ;;
    --patterns-file) PATTERNS_FILE="$2"; shift 2 ;;
    --strict)        STRICT=1; shift ;;
    --json)          JSON=1; shift ;;
    -h|--help)       sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "gate-danger: 未知参数 $1" >&2; exit 3 ;;
  esac
done

# 取待检内容
if [[ -n "$SCAN_FILE" ]]; then
  [[ -r "$SCAN_FILE" ]] || { echo "gate-danger: 读不到 $SCAN_FILE" >&2; exit 3; }
  CONTENT=$(cat "$SCAN_FILE")
elif [[ -n "$SCAN_TEXT" ]]; then
  CONTENT="$SCAN_TEXT"
else
  echo "gate-danger: 需 --scan-text 或 --scan-file" >&2; exit 3
fi

# 危险模式：内置默认（ERE）；--patterns-file 覆盖
PATTERNS=(
  'rm[[:space:]]+-[a-z]*[rf]'                 # 递归/强制删除
  'git[[:space:]]+push'                       # 对外发布
  'git[[:space:]]+reset[[:space:]]+--hard'    # 毁工作区
  'git[[:space:]]+clean[[:space:]]+-[a-z]*f'
  '(^|[[:space:]])sudo[[:space:]]'            # 提权
  '(drop|truncate)[[:space:]]+table'          # 毁库
  'chmod[[:space:]]+-R'
  '>[[:space:]]*/dev/(sd|disk|nvme)'          # 写裸盘
  'curl[[:space:]].*\|[[:space:]]*(bash|sh)'  # 远程管道执行
)
if [[ -n "$PATTERNS_FILE" ]]; then
  PATTERNS=()
  while IFS= read -r p; do [[ -n "$p" ]] && PATTERNS+=("$p"); done < "$PATTERNS_FILE"
fi

hits=(); ln=0
while IFS= read -r line; do
  ln=$((ln+1))
  for p in "${PATTERNS[@]}"; do
    if printf '%s' "$line" | grep -Eq -- "$p"; then
      frag=$(printf '%s' "$line" | sed 's/^[[:space:]]*//' | cut -c1-60)
      hits+=("{pattern:[$p], line:$ln, hit:[$frag]}")
      [[ $STRICT -eq 1 ]] && { printf '%s\n' "${hits[@]}"; exit 10; }
    fi
  done
done <<< "$CONTENT"

if [[ ${#hits[@]} -gt 0 ]]; then
  if [[ $JSON -eq 1 ]]; then
    printf '['
    for i in "${!hits[@]}"; do
      [[ $i -gt 0 ]] && printf ','
      printf '"%s"' "${hits[$i]//\"/\\\"}"
    done
    printf ']\n'
  else
    printf '%s\n' "${hits[@]}"
  fi
  exit 10
fi
echo "gate-danger: 无危险命中"
exit 0
