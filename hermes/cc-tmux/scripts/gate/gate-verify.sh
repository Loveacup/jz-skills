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
#   --cmd "<命令>"           验收命令，可重复；逐条执行并抓退出码
#   --artifact "<路径>"      产物路径，可重复；须存在且 size>0
#   --expect-artifacts <glob> 前置硬门：在客观验收【之前】先验 glob 匹配的文件存在且非空。
#                            可重复，或单值逗号分隔多 glob。零匹配=缺失。任一缺失 → exit 10
#                            （硬门，与 gate-danger 同语义，不可绕过）。不传则行为完全不变。
#   --cwd <dir>              命令工作目录（默认当前目录）
#   --json                  结构化 JSON 数组输出
#   -h|--help               打印本头注
#
# 退出码： 0 全部 criterion 过 · 1 某命令非零退出 · 2 某产物缺失/0字节 · 3 参数错误
#          · 10 --expect-artifacts 前置产物缺失/0字节（硬门，gate-danger 同语义）
# stdout： 逐条 criterion → {evidence, verdict}（--json 时为 JSON 数组）
# stderr： 机器元数据（命令、退出码原值、耗时）
#
# 示例：
#   bash gate-verify.sh --cmd "npm test" --artifact /tmp/out.md --json
#   # 0 → 客观半过，交 auditor 审主观半；1/2 → 直接退回 CC（计数），不劳 agent
#   bash gate-verify.sh --expect-artifacts "/tmp/cc-output/*.md" --cmd "npm test"
#   # 产物 glob 先验：任一缺失/0字节 → exit 10（硬门），命令根本不跑
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

CMDS=(); ARTIFACTS=(); EXPECT=(); CWD="."; JSON=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cmd)              CMDS+=("$2"); shift 2 ;;
    --artifact)         ARTIFACTS+=("$2"); shift 2 ;;
    --expect-artifacts) EXPECT+=("$2"); shift 2 ;;
    --cwd)              CWD="$2"; shift 2 ;;
    --json)             JSON=1; shift ;;
    -h|--help)          sed -n '2,31p' "$0"; exit 0 ;;
    *) echo "gate-verify: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ ${#CMDS[@]} -eq 0 && ${#ARTIFACTS[@]} -eq 0 && ${#EXPECT[@]} -eq 0 ]] && { echo "gate-verify: 至少需 --cmd / --artifact / --expect-artifacts" >&2; exit 3; }

# ── 前置硬门：--expect-artifacts 产物存在性（在任何客观验收之前）──────────────
# 每个 glob 先用 shell 展开（nullglob：零匹配=空），再对每个命中 find -L（跟随符号链接）
# 求 -type f -size +0c。零匹配 或 任一文件缺失/0字节 → exit 10（gate-danger 同语义，硬门）。
if [[ ${#EXPECT[@]} -gt 0 ]]; then
  shopt -s nullglob
  for raw in "${EXPECT[@]}"; do
    # 单值逗号分隔 → 拆多 glob
    IFS=',' read -ra _globs <<< "$raw"
    for g in "${_globs[@]}"; do
      g="${g#"${g%%[![:space:]]*}"}"; g="${g%"${g##*[![:space:]]}"}"   # trim 两端空白
      [[ -z "$g" ]] && continue
      # shellcheck disable=SC2206  # 故意 word-split + glob 展开
      _matches=( $g )
      if [[ ${#_matches[@]} -eq 0 ]]; then
        echo "gate-verify: expect-artifacts glob [$g] 零匹配（产物缺失）" >&2
        echo "expect-artifact:[$g] -> {evidence:[no match], verdict:fail}"
        exit 10
      fi
      for m in "${_matches[@]}"; do
        if [[ -n "$(find -L "$m" -type f -size +0c 2>/dev/null | head -n1)" ]]; then
          :
        else
          echo "gate-verify: expect-artifacts [$m] 缺失或 0 字节" >&2
          echo "expect-artifact:[$m] -> {evidence:[missing or empty], verdict:fail}"
          exit 10
        fi
      done
    done
  done
  shopt -u nullglob
fi

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

if [[ ${#results[@]} -gt 0 ]]; then
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
fi
exit $rc
