#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-gc.sh —— OMP 状态文件垃圾回收
#
# 纯 bash + jq + 文件系统，可独立运行（不依赖 omp / Hermes）。
#
# 三条安全规则（与 cc-gc 同源）：
#   1. 绝不删 running 状态的任何文件——即便超龄；async pid 存活更是绝对保护。
#   2. accepted 必须已归档（omp-archive/<id>/）才清 /tmp 残留；未归档只提示。
#   3. 默认干运行（只读建议）；--apply 才真删，且只删 ① accepted 已归档残留
#      ② created/gated/rejected 且超龄(默认>24h) ③ 无主状态的孤儿文件且超龄。
#
# Usage:
#   omp-gc.sh [--mode scan|gc] [--apply] [--max-age-h N]
#     scan   全量扫描 → 表格摘要（默认）
#     gc     列候选 + 建议；加 --apply 执行清理
#
# 可注入：OMP_TMPDIR（状态文件基目录，默认 /tmp）
# 退出码： 0 正常 · 2 参数错误
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SELF_DIR/lib/omp-lib.sh"

MODE="scan"; APPLY=false; MAX_AGE_H=24
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    --max-age-h) MAX_AGE_H="$2"; shift 2 ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "omp-gc: 未知参数 $1" >&2; exit 2 ;;
  esac
done
case "$MODE" in scan|gc) ;; *) echo "omp-gc: --mode 须 scan|gc" >&2; exit 2 ;; esac
NOW=$(now_epoch); MAX_AGE=$((MAX_AGE_H * 3600))

ACTIVE=0 ZOMBIE=0 NEED_ARCHIVE=0 CLEANABLE=0 STALE=0 ORPHAN=0 TOTAL=0
LINES=""; APPLIED=0

del_task_files() {  # 删某 task_id 的全部 /tmp 工作文件（不含归档）
  local id="$1"
  rm -f "$(state_path "$id")" "$(raw_path "$id")" "$(raw_path "$id").err" \
        "$(raw_path "$id").exit" \
        "$(prompt_path "$id")" "$(counter_path "$id")" \
        "$OMP_TMPDIR/omp-pkg-${id}.json" "$OMP_TMPDIR/omp-verdict-${id}.yaml" "$(fifo_path "$id")" 2>/dev/null || true
}

# ═══ 1) 遍历状态文件 ═══════════════════════════════════════════════
for sf in "$OMP_TMPDIR"/omp-state-*.json; do
  [[ -e "$sf" ]] || continue
  TOTAL=$((TOTAL+1))
  id=$(jq -r '.task_id // empty' "$sf" 2>/dev/null || echo "")
  [[ -z "$id" ]] && { id=$(basename "$sf" .json); id="${id#omp-state-}"; }
  if ! validate_task_id "$id"; then
    LINES="${LINES}  🚫 unsafe   $(basename "$sf")（非法 task_id，跳过）"$'\n'
    continue
  fi
  status=$(jq -r '.status // "?"' "$sf" 2>/dev/null || echo "?")
  pid=$(jq -r '.run.pid // .run.rpc_pid // empty' "$sf" 2>/dev/null || echo "")
  age=$(( NOW - $(get_mtime "$sf") ))
  ageh=$(( age / 3600 ))

  case "$status" in
    running)
      if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        ACTIVE=$((ACTIVE+1))
        LINES="${LINES}  🟢 active   ${id}（running, pid=$pid 存活）→ 保护，不碰"$'\n'
      else
        ZOMBIE=$((ZOMBIE+1))
        LINES="${LINES}  🧟 zombie   ${id}（running 但 pid=${pid:-?} 已死，${ageh}h）→ 人工确认后 omp-finish --reject/--human-review；gc 不自动删 running"$'\n'
      fi
      ;;
    accepted)
      if [[ -d "$(archive_dir "$id")" ]]; then
        CLEANABLE=$((CLEANABLE+1))
        LINES="${LINES}  ✅ done     ${id}（accepted, 已归档）→ 可清 /tmp 残留"$'\n'
        if [[ "$MODE" == "gc" && "$APPLY" == true ]]; then del_task_files "$id"; APPLIED=$((APPLIED+1)); LINES="${LINES}     🧹 已清理 /tmp 残留（归档保留）"$'\n'; fi
      else
        NEED_ARCHIVE=$((NEED_ARCHIVE+1))
        LINES="${LINES}  📦 archive? ${id}（accepted 但无归档目录）→ 先确认归档，暂不清"$'\n'
      fi
      ;;
    created|gated|rejected)
      if [[ "$age" -gt "$MAX_AGE" ]]; then
        STALE=$((STALE+1))
        LINES="${LINES}  💤 stale    ${id}（$status, ${ageh}h>${MAX_AGE_H}h）→ 可清"$'\n'
        if [[ "$MODE" == "gc" && "$APPLY" == true ]]; then del_task_files "$id"; APPLIED=$((APPLIED+1)); LINES="${LINES}     🧹 已清理全部 /tmp 文件"$'\n'; fi
      else
        LINES="${LINES}  ⏳ recent   ${id}（$status, ${ageh}h）→ 近期，保留"$'\n'
      fi
      ;;
    *)
      LINES="${LINES}  ❔ unknown  ${id}（status=${status}）→ 人工查看"$'\n'
      ;;
  esac
done

# ═══ 2) 孤儿文件（无对应 state） ═══════════════════════════════════
for f in "$OMP_TMPDIR"/omp-raw-*.json "$OMP_TMPDIR"/omp-prompt-*.txt \
         "$OMP_TMPDIR"/omp-pkg-*.json "$OMP_TMPDIR"/omp-counter-*.json \
         "$OMP_TMPDIR"/omp-verdict-*.yaml; do
  [[ -e "$f" ]] || continue
  b=$(basename "$f")
  id="$b"; id="${id#omp-raw-}"; id="${id#omp-prompt-}"; id="${id#omp-pkg-}"
  id="${id#omp-counter-}"; id="${id#omp-verdict-}"; id="${id%.json}"; id="${id%.txt}"; id="${id%.yaml}"
  if ! validate_task_id "$id"; then
    LINES="${LINES}  🚫 unsafe   ${b}（非法 task_id，跳过）"$'\n'
    continue
  fi
  [[ -f "$(state_path "$id")" ]] && continue   # 有主，不算孤儿
  age=$(( NOW - $(get_mtime "$f") )); ageh=$(( age / 3600 ))
  ORPHAN=$((ORPHAN+1))
  if [[ "$age" -gt "$MAX_AGE" ]]; then
    LINES="${LINES}  🗑️ orphan   ${b}（无主, ${ageh}h>${MAX_AGE_H}h）→ 可清"$'\n'
    if [[ "$MODE" == "gc" && "$APPLY" == true ]]; then rm -f "$f" 2>/dev/null || true; APPLIED=$((APPLIED+1)); fi
  else
    LINES="${LINES}  🗑️ orphan   ${b}（无主, ${ageh}h，未超龄）→ 暂留"$'\n'
  fi
done

# ═══ 输出 ═════════════════════════════════════════════════════════
echo "===📡 BEGIN omp-gc (relay verbatim)==="
if [[ "$MODE" == "gc" && "$APPLY" == true ]]; then
  echo "🧹 omp-gc（--apply：已执行清理 $APPLIED 项；running 一律保护不碰）"
else
  echo "🔍 omp-gc（${MODE}${APPLY:+ }·干运行只读，未删任何文件）"
fi
echo "📊 state 总数=$TOTAL · active=$ACTIVE · zombie=$ZOMBIE · accepted可清=$CLEANABLE · 待归档=$NEED_ARCHIVE · stale=$STALE · 孤儿=$ORPHAN"
if [[ -n "$LINES" ]]; then echo "  ── 明细 ──"; printf '%s' "$LINES"; else echo "  ✓ 无 OMP 状态/产物文件"; fi
echo "  ℹ️ 安全: 绝不删 running · accepted 须先归档 · 默认干运行（--apply 才清）"
echo "===📡 END==="
exit 0
