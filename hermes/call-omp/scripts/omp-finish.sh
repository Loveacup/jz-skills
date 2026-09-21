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
require_task_id "$TASK_ID" || exit 3
STATUS=$(jq -r '.status' "$STATE")
MON_MODE=$(jq -r '.package.mode // ""' "$STATE"); MON_MODE="${MON_MODE%%:*}"
RAW=$(jq -r '.run.raw_output // empty' "$STATE")
EXPECTED_RAW=$(raw_path "$TASK_ID")
[[ -z "$RAW" || "$RAW" == "$EXPECTED_RAW" ]] || { echo "omp-finish: state raw_output 非规范路径" >&2; exit 3; }
RAW="$EXPECTED_RAW"
RUN_EC=$(jq -r '.run.exit_code // empty' "$STATE")
RUN_STOP=$(jq -r '.monitor.stop_reason // .run.stop_reason // empty' "$STATE")

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

# ── P1B：required_actions 双写（加性、向后兼容；与 legacy next_action 并列）──
# monitor 已持久化的结构化动作列表（可能为 null / legacy 缺失）。作为“已被 P1A gate 校验过”的候选来源，
# 但在此仍二次过 P1A 校验器把关，绝不让畸形/缺失数据泄成一条无效 YAML 动作。
PY="${PYTHON:-python3}"
VALIDATOR="$SELF_DIR/required-actions-validate.py"
MON_RA=$(jq -c '.monitor.required_actions // empty' "$STATE" 2>/dev/null || true)

# ra_single <kind> <reason-raw> → 单动作数组 JSON（reason 去控制符、去换行、裁 ≤512、保证非空）
ra_single() {
  local kind="$1" reason
  reason=$(printf '%s' "${2:-}" | jq -Rrs 'gsub("[\\u0000-\\u001f]";" ") | .[0:512]' 2>/dev/null || true)
  [[ -n "$reason" ]] || reason="需按审计结论处理（未提供具体理由）"
  jq -cn --arg k "$kind" --arg r "$reason" '[{kind:$k,reason:$r}]'
}

# build_required_actions <next_action> → 校验通过的 required_actions JSON 数组（flow-style YAML 直用）
build_required_actions() {
  local na="$1" ra=""
  case "$na" in
    accept)
      ra='[]' ;;
    human_review)
      ra=$(ra_single human_review "$REASON") ;;
    stop)
      ra=$(ra_single stop "$REASON") ;;
    revise|*)
      # 普通 reject：优先用 monitor 已校验的非空动作列表；否则派生一条 revise。
      if [[ -n "$MON_RA" && "$MON_RA" != "null" ]] \
         && printf '%s' "$MON_RA" | jq -e 'type=="array" and length>0' >/dev/null 2>&1 \
         && "$PY" "$VALIDATOR" --json "$MON_RA" >/dev/null 2>&1; then
        ra="$MON_RA"
      else
        local rr="$REASON"; [[ -n "$rr" ]] || rr="$RINSTR"
        ra=$(ra_single revise "$rr")
      fi ;;
  esac
  # 终局把关：任何原因不过 P1A 校验 → 退回一条基于当前裁决的安全动作（不采信畸形数据）。
  if ! "$PY" "$VALIDATOR" --json "$ra" >/dev/null 2>&1; then
    case "$na" in
      accept)       ra='[]' ;;
      stop)         ra=$(ra_single stop "自动循环已达硬终止，须停止并升级人工。") ;;
      human_review) ra=$(ra_single human_review "需人工复核后再继续。") ;;
      *)            ra=$(ra_single revise "需按审计结论进行有界修复。") ;;
    esac
  fi
  printf '%s' "$ra"
}

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
  # P1B：与 legacy next_action 并列的结构化动作列表（JSON flow-style = 合法 YAML；已过 P1A 校验）。
  printf 'required_actions: %s\n' "$(build_required_actions "$na")"
  [[ -n "$REASON" ]] && printf 'decision_reason: %s\n' "$(printf '%s' "$REASON" | jq -R -s '.')"
  echo "decided_by: hermes"
  echo "decided_at: $(now_iso)"
}

cleanup_tmp() {  # 清理 /tmp 工作文件（保留归档）
  $KEEP && { echo "   （--keep：保留所有产物）"; return; }
  rm -f "$(prompt_path "$TASK_ID")" "$OMP_TMPDIR/omp-pkg-${TASK_ID}.json" \
        "$(counter_path "$TASK_ID")" "$RAW.err" "$RAW.exit" 2>/dev/null || true
}

# 进入裁决 = RPC daemon 使命结束，关闭（幂等；raw 已落盘，verdict 提取不依赖 daemon）
rpc_stop "$TASK_ID" "$(jq -r '.run.rpc_pid // empty' "$STATE")" "$(jq -r '.run.holder_pid // empty' "$STATE")"

EXITCODE=0
echo "===📋 BEGIN omp-finish (relay verbatim)==="

case "$DECISION" in
  accept)
    # ── 红线校验 ──
    [[ "$STATUS" == "reported" ]] || { echo "🚫 accept 拒绝：status=${STATUS}（须 reported；先 monitor）"; echo "===📋 END==="; exit 2; }
    [[ -z "$RUN_EC" || "$RUN_EC" == "0" ]] || { echo "🚫 accept 拒绝：OMP exit_code=${RUN_EC}"; echo "===📋 END==="; exit 2; }
    [[ "$RUN_STOP" == "stop" ]] || { echo "🚫 accept 拒绝：stopReason=${RUN_STOP:-unknown}（须 stop）"; echo "===📋 END==="; exit 2; }
    [[ "$SEV" != "blocker" ]]     || { echo "🚫 accept 拒绝：severity=blocker 是红线，不可接受。改用 --reject / --human-review"; echo "===📋 END==="; exit 2; }
    [[ "$MON_MODE" == "execute" || "$EVN" -gt 0 ]] || { echo "🚫 accept 拒绝：evidence 为空，不采信无证据的完成"; echo "===📋 END==="; exit 2; }
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
