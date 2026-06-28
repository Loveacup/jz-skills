#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-finish.sh —— 四步④：转 Hermes verdict + 裁决 + 归档/计数/清理
#
# 职责：把 monitor 的结论转成 Hermes verdict（severity/evidence/reject_instruction/next_action），
#       按 Hermes 裁决落定状态：
#   --accept        status=accepted，归档到 omp-archive/<id>/，清理 /tmp 工作文件。
#                   红线：status 必须 reported；severity=blocker 不可 accept；evidence 不可空。
#   --reject        status=rejected，保留产物供分析；gate-counter --inc-reject（可能触发 stop）。
#   --human-review  status=rejected + human_review 标记，升级人工（不占 reject 重试配额）。
#
# 参数：
#   --state <file> / --task-id <id>   状态文件（二选一）
#   --accept | --reject | --human-review   裁决（三选一，必填）
#   --reason "<文本>"   人工决策理由（记入 verdict，可选）
#   --keep             不清理 /tmp 工作文件（调试用；accept 默认清理、保留归档）
#   -h|--help
#
# 退出码： 0 裁决落定 · 2 accept 违反红线（blocker/空证据/非 reported）· 3 参数错误
#          · 20 reject 触发轮次/次数硬终止（next_action=stop）
# stdout： Hermes verdict YAML（同时写 archive 或保留在产物旁）
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SELF_DIR/lib/omp-lib.sh"
GATE="$SELF_DIR/gate"

STATE=""; TASK_ID=""; DECISION=""; REASON=""; KEEP=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state)        STATE="$2"; shift 2 ;;
    --task-id)      TASK_ID="$2"; shift 2 ;;
    --accept)       DECISION="accept"; shift ;;
    --reject)       DECISION="reject"; shift ;;
    --human-review) DECISION="human_review"; shift ;;
    --reason)       REASON="$2"; shift 2 ;;
    --keep)         KEEP=true; shift ;;
    -h|--help)      sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "omp-finish: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ -z "$STATE" && -n "$TASK_ID" ]] && STATE="$(state_path "$TASK_ID")"
[[ -n "$STATE" && -r "$STATE" ]] || { echo "omp-finish: 读不到状态文件" >&2; exit 3; }
[[ -n "$DECISION" ]] || { echo "omp-finish: 须三选一 --accept|--reject|--human-review" >&2; exit 3; }

TASK_ID=$(jq -r '.task_id' "$STATE")
STATUS=$(jq -r '.status' "$STATE")
RAW=$(jq -r '.run.raw_output // empty' "$STATE")

update_state() { local f="$1"; local s; s=$(jq "$f | .updated_at=\"$(now_iso)\"" "$STATE"); printf '%s' "$s" | atomic_write "$STATE"; }

# ── 取内层审计 JSON（优先 monitor.inner，缺则从 raw 重提）──
INNER=$(jq -c '.monitor.inner // empty' "$STATE" 2>/dev/null || true)
if [[ -z "$INNER" || "$INNER" == "null" ]]; then
  if [[ -s "$RAW" ]]; then INNER=$(extract_inner_json "$(jsonl_final_text "$RAW")"); fi
fi
SEV="unknown"; SUMMARY=""; RINSTR=""; EVN=0
if [[ -n "$INNER" ]] && inner_json_valid "$INNER"; then
  SEV=$(printf '%s' "$INNER" | jq -r '.severity // "unknown"')
  SUMMARY=$(printf '%s' "$INNER" | jq -r '.summary // ""')
  RINSTR=$(printf '%s' "$INNER" | jq -r '.reject_instruction // ""')
  EVN=$(printf '%s' "$INNER" | jq -r 'if (.evidence|type)=="array" then (.evidence|length) else 0 end')
fi

# ── build_verdict <next_action> → YAML 到 stdout ──
build_verdict() {
  local na="$1"
  echo "task_id: $TASK_ID"
  echo "severity: $SEV"
  printf 'summary: %s\n' "$(printf '%s' "$SUMMARY" | jq -R -s '.' )"
  echo "evidence:"
  if [[ -n "$INNER" ]] && inner_json_valid "$INNER"; then
    printf '%s' "$INNER" | jq -r '.evidence[]? | "  - type: \(.type // "reference")\n    ref: \((.ref // (.|tostring)) | tojson)"'
  fi
  [[ "$EVN" -eq 0 ]] && echo "  []"
  printf 'reject_instruction: %s\n' "$(printf '%s' "$RINSTR" | jq -R -s '.')"
  echo "next_action: $na"
  [[ -n "$REASON" ]] && printf 'decision_reason: %s\n' "$(printf '%s' "$REASON" | jq -R -s '.')"
  echo "decided_by: hermes"
  echo "decided_at: $(now_iso)"
}

cleanup_tmp() {  # 清理 /tmp 工作文件（保留归档）
  $KEEP && { echo "   （--keep：保留所有产物）"; return; }
  rm -f "$(prompt_path "$TASK_ID")" "$OMP_TMPDIR/omp-pkg-${TASK_ID}.json" \
        "$(counter_path "$TASK_ID")" "$RAW.err" 2>/dev/null || true
}

# 进入裁决 = RPC daemon 使命结束，关闭（幂等；raw 已落盘，verdict 提取不依赖 daemon）
rpc_stop "$TASK_ID" "$(jq -r '.run.rpc_pid // empty' "$STATE")" "$(jq -r '.run.holder_pid // empty' "$STATE")"

EXITCODE=0
echo "===📋 BEGIN omp-finish (relay verbatim)==="

case "$DECISION" in
  accept)
    # ── 红线校验 ──
    [[ "$STATUS" == "reported" ]] || { echo "🚫 accept 拒绝：status=${STATUS}（须 reported；先 monitor）"; echo "===📋 END==="; exit 2; }
    [[ "$SEV" != "blocker" ]]     || { echo "🚫 accept 拒绝：severity=blocker 是红线，不可接受。改用 --reject / --human-review"; echo "===📋 END==="; exit 2; }
    [[ "$EVN" -gt 0 ]]            || { echo "🚫 accept 拒绝：evidence 为空，不采信无证据的完成"; echo "===📋 END==="; exit 2; }
    VERDICT=$(build_verdict accept)
    update_state ".status=\"accepted\" | .verdict=$(printf '%s' "$VERDICT" | jq -R -s '{yaml:.}')"
    # 归档
    AD="$(archive_dir "$TASK_ID")"; mkdir -p "$AD"
    cp -f "$STATE" "$AD/state.json" 2>/dev/null || true
    [[ -s "$RAW" ]] && cp -f "$RAW" "$AD/raw.jsonl" 2>/dev/null || true
    [[ -s "$(prompt_path "$TASK_ID")" ]] && cp -f "$(prompt_path "$TASK_ID")" "$AD/prompt.txt" 2>/dev/null || true
    printf '%s\n' "$VERDICT" > "$AD/verdict.yaml"
    echo "✅ ACCEPTED · task_id=$TASK_ID · severity=$SEV · evidence=$EVN 条"
    echo "   归档: $AD/"
    cleanup_tmp
    ;;
  reject)
    set +e
    C_OUT=$(bash "$GATE/gate-counter.sh" --task-id "$TASK_ID" --inc-reject 2>/dev/null); C_RC=$?
    set -e
    REJN=$(echo "$C_OUT" | jq -r '.reject_count' 2>/dev/null || echo "?")
    if [[ $C_RC -eq 20 ]]; then NA="stop"; EXITCODE=20; else NA="revise"; fi
    VERDICT=$(build_verdict "$NA")
    update_state ".status=\"rejected\" | .verdict=$(printf '%s' "$VERDICT" | jq -R -s '{yaml:.}')"
    printf '%s\n' "$VERDICT" > "$OMP_TMPDIR/omp-verdict-${TASK_ID}.yaml"
    echo "↩️  REJECTED · task_id=$TASK_ID · reject_count=$REJN · next_action=$NA"
    [[ "$NA" == "stop" ]] && echo "   ⛔ reject 超限，硬终止：停循环，升级人工 / 转 cc-tmux"
    echo "   产物保留供分析: $RAW"
    ;;
  human_review)
    NA="human_review"
    VERDICT=$(build_verdict "$NA")
    update_state ".status=\"rejected\" | .human_review=true | .verdict=$(printf '%s' "$VERDICT" | jq -R -s '{yaml:.}')"
    printf '%s\n' "$VERDICT" > "$OMP_TMPDIR/omp-verdict-${TASK_ID}.yaml"
    echo "🧑‍⚖️ HUMAN_REVIEW · task_id=$TASK_ID · 升级人工复核（不占 reject 配额）"
    echo "   产物保留: $RAW"
    ;;
esac

echo "--- Hermes verdict ---"
printf '%s\n' "$VERDICT"
echo "===📋 END==="
exit $EXITCODE
