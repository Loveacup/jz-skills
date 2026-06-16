#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# gate-verify.sh —— 客观验收 gate
#
# 【基质无关】 不依赖 tmux / cc-tmux 运行时；纯参数进、退出码出。
# 【零 tmux 耦合】不读 tmux pane、不碰 cc-* 状态文件；任何 agent/编排基质可直接调。
# 【提升条件】 当前唯一消费者 cc-tmux，暂居 cc-tmux/scripts/gate/；
#              出现第 2 消费者 → 整组 gate-*.sh 提升为独立 audit skill（裁决③ 复活）。
#
# 职责：此刻重新执行验收命令、抓退出码；检查每个产物存在且非 0 字节。不读历史运行结果。
#
# 参数：
#   --cmd "<命令>"       验收命令，可重复；逐条执行并抓退出码
#   --artifact "<路径>"  产物路径，可重复；须存在且 size>0
#   --cwd <dir>          命令工作目录（默认当前目录）
#   --json               结构化 JSON 数组输出
#   -h|--help            打印本头注
#
# 退出码： 0 全部 criterion 过 · 1 某命令非零退出 · 2 某产物缺失/0字节 · 3 参数错误
# stdout： 逐条 criterion → {evidence, verdict}（--json 时为 JSON 数组）
# stderr： 机器元数据（命令、退出码原值、耗时）
#
# 示例：
#   bash gate-verify.sh --cmd "npm test" --artifact /tmp/out.md --json
#   # 0 → 客观半过，交 auditor 审主观半；1/2 → 直接退回 CC（计数），不劳 agent
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

CMDS=(); ARTIFACTS=(); CWD="."; JSON=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cmd)      CMDS+=("$2"); shift 2 ;;
    --artifact) ARTIFACTS+=("$2"); shift 2 ;;
    --cwd)      CWD="$2"; shift 2 ;;
    --json)     JSON=1; shift ;;
    -h|--help)  sed -n '2,33p' "$0"; exit 0 ;;
    *) echo "gate-verify: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ ${#CMDS[@]} -eq 0 && ${#ARTIFACTS[@]} -eq 0 ]] && { echo "gate-verify: 至少需 --cmd 或 --artifact" >&2; exit 3; }

results=(); rc=0

# 客观半①：逐条命令此刻重跑、抓退出码（不信历史运行）
for c in "${CMDS[@]:-}"; do
  [[ -z "$c" ]] && continue
  t0=$SECONDS
  set +e; out=$(cd "$CWD" && eval "$c" 2>&1); code=$?; set -e
  if [[ $code -eq 0 ]]; then v=pass; else v=fail; rc=1; fi
  echo "cmd=[$c] exit=$code dur=$((SECONDS-t0))s" >&2
  ev=$(printf '%s' "$out" | tail -n 3 | tr '\n' ' ')
  results+=("cmd:[$c] -> {evidence:[$ev], verdict:$v}")
done

# 客观半②：逐个产物须存在且非 0 字节
for a in "${ARTIFACTS[@]:-}"; do
  [[ -z "$a" ]] && continue
  if [[ -s "$a" ]]; then sz=$(wc -c < "$a" | tr -d ' '); v=pass
  else sz=0; v=fail; [[ $rc -eq 0 ]] && rc=2; fi
  results+=("artifact:[$a] -> {evidence:[size=${sz}B], verdict:$v}")
done

if [[ $JSON -eq 1 ]]; then
  printf '['
  for i in "${!results[@]}"; do
    [[ $i -gt 0 ]] && printf ','
    printf '"%s"' "${results[$i]//\"/\\\"}"
  done
  printf ']\n'
else
  printf '%s\n' "${results[@]}"
fi
exit $rc
