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
#   --attempt-id <uuid> --launch-fingerprint <hex64>
#                      execute attempt 必填：须等于 state 当前 attempt；缺失 exit 3，不符 exit 2（state 不变）
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

STATE=""; TASK_ID=""; DECISION=""; REASON=""; KEEP=false; EXPECT_AID=""; EXPECT_FP=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state)        STATE="$2"; shift 2 ;;
    --task-id)      TASK_ID="$2"; shift 2 ;;
    --accept)       DECISION="accept"; shift ;;
    --reject)       DECISION="reject"; shift ;;
    --human-review) DECISION="human_review"; shift ;;
    --reason)       REASON="$2"; shift 2 ;;
    --attempt-id)   EXPECT_AID="$2"; shift 2 ;;
    --launch-fingerprint) EXPECT_FP="$2"; shift 2 ;;
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
trap 'lifecycle_lock_release 2>/dev/null || true' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
if ! lifecycle_lock_acquire "$TASK_ID"; then
  echo "omp-finish: 任务 $TASK_ID 生命周期锁被占用；拒绝并发裁决" >&2
  exit 2
fi
STATUS=$(jq -r '.status' "$STATE")
MON_MODE=$(jq -r '.package.mode // ""' "$STATE"); MON_MODE="${MON_MODE%%:*}"
RAW=$(jq -r '.run.raw_output // empty' "$STATE")
EXPECTED_RAW=$(raw_path "$TASK_ID")
[[ -z "$RAW" || "$RAW" == "$EXPECTED_RAW" ]] || { echo "omp-finish: state raw_output 非规范路径" >&2; exit 3; }
RAW="$EXPECTED_RAW"
RUN_EC=$(jq -r '.run.exit_code // empty' "$STATE")
RUN_STOP=$(jq -r '.monitor.stop_reason // .run.stop_reason // empty' "$STATE")

update_state() { local f="$1"; local s; s=$(jq "$f | .updated_at=\"$(now_iso)\"" "$STATE"); printf '%s' "$s" | atomic_write "$STATE"; }

execute_receipt_terminal_clean() {
  local aid fp rs ps cf ci cipid st
  aid=$(jq -r '.run.attempt_id // empty' "$STATE")
  fp=$(jq -r '.run.launch_fingerprint // empty' "$STATE")
  rs="$(resource_state_path "$TASK_ID")"; ps="$(pid_store_path "$TASK_ID")"; cf="$(control_file_path "$TASK_ID")"
  validate_attempt_id "$aid" && [[ "$fp" =~ ^[0-9a-f]{64}$ ]] || return 1
  [[ "$(jq -r '.run.resource_state // empty' "$STATE")" == "$rs" \
     && "$(jq -r '.run.pid_store // empty' "$STATE")" == "$ps" \
     && "$(jq -r '.run.control_file // empty' "$STATE")" == "$cf" \
     && -f "$rs" && ! -L "$rs" ]] || return 1
  jq -e --arg tid "$TASK_ID" --arg aid "$aid" --arg fp "$fp" \
    --arg sf "$rs" --arg ro "$(raw_path "$TASK_ID")" --arg ps "$ps" --arg cf "$cf" '
    .schema=="call-omp-resource-supervisor.v2" and .capture_mode=="execute_v1" and
    .task_id==$tid and .attempt_id==$aid and .launch_fingerprint==$fp and
    .state_file==$sf and .raw_output==$ro and .control_file==$cf and .run.pid_store==$ps and
    ((.status=="reported") or (.status=="rejected")) and .cleanup_confirmed==true and
    (.terminal_reason|type)=="string" and (.child_identity|type)=="object" and
    .exit_code==.worker_exit_code and
    ((.worker_exit_code==null) or
      ((.worker_exit_code|type)=="number" and .worker_exit_code==(.worker_exit_code|floor))) and
    ((.supervisor_exit_code|type)=="number" and
      .supervisor_exit_code==(.supervisor_exit_code|floor))' "$rs" >/dev/null 2>&1 || return 1
  ci=$(jq -c '.child_identity' "$rs")
  st=$(jq -r '.status' "$rs")
  [[ -f "$ps" && ! -L "$ps" ]] || return 1
  jq -e --arg tid "$TASK_ID" --arg aid "$aid" --arg fp "$fp" \
    --arg sf "$rs" --arg ro "$(raw_path "$TASK_ID")" --arg ps "$ps" --arg cf "$cf" \
    --arg st "$st" --argjson ci "$ci" '
    .schema=="call-omp-execute-identity.v1" and .capture_mode=="execute_v1" and
    .task_id==$tid and .attempt_id==$aid and .launch_fingerprint==$fp and
    .state_file==$sf and .raw_output==$ro and .pid_store==$ps and .control_file==$cf and
    .status==$st and .cleanup_confirmed==true and .child_identity==$ci' \
    "$ps" >/dev/null 2>&1
}

execute_receipt_accept_ready() {
  execute_receipt_terminal_clean || return 1
  [[ "$(jq -r '.run.cancel_requested // false' "$STATE")" != "true" ]] || return 1
  local rs; rs="$(resource_state_path "$TASK_ID")"
  jq -e '.status=="reported" and .worker_exit_code==0 and .exit_code==0 and
         .supervisor_exit_code==0 and .cleanup_confirmed==true' "$rs" >/dev/null 2>&1
}

EXECUTION_SUPERVISED=$(jq -r '.run.execution_supervised // false' "$STATE")

# Caller attempt fence: an execute decision names the attempt it is about.
# A late FINISH from a replaced attempt must never accept, reject or stop
# the successor that now owns the same task state.
if [[ "$EXECUTION_SUPERVISED" == "true" ]]; then
  if [[ -z "$EXPECT_AID" || -z "$EXPECT_FP" ]]; then
    echo "omp-finish: execute 裁决必须带 --attempt-id 与 --launch-fingerprint（当前 attempt 身份）" >&2
    exit 3
  fi
  if ! jq -e --arg aid "$EXPECT_AID" --arg fp "$EXPECT_FP" \
      '.run.attempt_id==$aid and .run.launch_fingerprint==$fp' "$STATE" >/dev/null 2>&1; then
    echo "omp-finish: attempt 身份与当前 state 不符（迟到或已被替换的 attempt）；拒绝裁决，state 未改" >&2
    exit 2
  fi
elif [[ -n "$EXPECT_AID" || -n "$EXPECT_FP" ]]; then
  # No supervised attempt owns this state (e.g. a gated successor after START):
  # an attempt identity can only belong to a replaced attempt.
  echo "omp-finish: state 当前没有已发起的 execute attempt，所给身份属于已被替换的 attempt；拒绝裁决，state 未改" >&2
  exit 2
elif [[ "$MON_MODE" == "execute" && "$STATUS" != "rejected" ]]; then
  # An execute state with no launched attempt (gated/created successor) has
  # nothing to decide; an identity-less decision here can only be a late write
  # meant for a replaced attempt. A state SEND already rejected pre-launch may
  # still be re-affirmed without identity.
  echo "omp-finish: execute state（status=${STATUS}）没有已发起的 attempt，无可裁决对象；拒绝，state 未改" >&2
  exit 3
fi

# Reject/human-review is also a lifecycle decision: an active execute attempt
# must first receive the authenticated control request. No PID signal fallback.
if [[ "$DECISION" != "accept" && "$EXECUTION_SUPERVISED" == "true" ]] \
   && ! execute_receipt_terminal_clean; then
  STOP_AID=$(jq -r '.run.attempt_id // empty' "$STATE")
  STOP_FP=$(jq -r '.run.launch_fingerprint // empty' "$STATE")
  if validate_attempt_id "$STOP_AID" && [[ "$STOP_FP" =~ ^[0-9a-f]{64}$ ]]; then
    lifecycle_lock_release
    set +e
    "$SELF_DIR/omp-stop.sh" --state "$STATE" --attempt-id "$STOP_AID" \
      --launch-fingerprint "$STOP_FP" --reason "${REASON:-omp-finish $DECISION}" --timeout 10
    STOP_RC=$?
    set -e
    if ! lifecycle_lock_acquire "$TASK_ID"; then
      echo "omp-finish: cancel 后无法重新取得生命周期锁" >&2
      exit 2
    fi
    if ! jq -e --arg tid "$TASK_ID" --arg aid "$STOP_AID" --arg fp "$STOP_FP" '
        .task_id==$tid and .run.execution_supervised==true and
        .run.capture_mode=="execute_v1" and .run.attempt_id==$aid and
        .run.launch_fingerprint==$fp' "$STATE" >/dev/null 2>&1; then
      echo "omp-finish: cancel 等待期间 attempt 已变化；拒绝裁决 successor attempt" >&2
      exit 2
    fi
  else
    update_state ".status=\"rejected\" | .run.cleanup_confirmed=false |
      .run.terminal_reason=\"cancel_identity_invalid\" |
      .monitor={checked_at:\"$(now_iso)\",issues:[\"finish requested rejection but execute identity is invalid; cleanup unknown\"]}"
  fi
  STATUS=$(jq -r '.status' "$STATE")
  RUN_EC=$(jq -r '.run.exit_code // empty' "$STATE")
  RUN_STOP=$(jq -r '.monitor.stop_reason // .run.stop_reason // empty' "$STATE")
fi

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
        "$(counter_path "$TASK_ID")" 2>/dev/null || true
  # execute_v1 receipt authenticates both streams on every later monitor call.
  [[ "$EXECUTION_SUPERVISED" == "true" ]] || rm -f "$RAW.err" "$RAW.exit" 2>/dev/null || true
}

# execute_v1 lifecycle is owned exclusively by supervisor/control-file; never
# route it through legacy rpc_stop PID signaling.
if [[ "$EXECUTION_SUPERVISED" != "true" ]]; then
  rpc_stop "$TASK_ID" "$(jq -r '.run.rpc_pid // empty' "$STATE")" "$(jq -r '.run.holder_pid // empty' "$STATE")"
fi

EXITCODE=0
echo "===📋 BEGIN omp-finish (relay verbatim)==="

case "$DECISION" in
  accept)
    # ── 红线校验 ──
    if [[ "$EXECUTION_SUPERVISED" == "true" ]] && ! execute_receipt_accept_ready; then
      echo "🚫 accept 拒绝：execute_v1 receipt 未匹配 clean reported terminal，或曾请求 cancellation"
      echo "===📋 END==="
      exit 2
    fi
    [[ "$STATUS" == "reported" ]] || { echo "🚫 accept 拒绝：status=${STATUS}（须 reported；先 monitor）"; echo "===📋 END==="; exit 2; }
    [[ -z "$RUN_EC" || "$RUN_EC" == "0" ]] || { echo "🚫 accept 拒绝：OMP exit_code=${RUN_EC}"; echo "===📋 END==="; exit 2; }
    [[ "$RUN_STOP" == "stop" ]] || { echo "🚫 accept 拒绝：stopReason=${RUN_STOP:-unknown}（须 stop）"; echo "===📋 END==="; exit 2; }
    [[ "$SEV" != "blocker" ]]     || { echo "🚫 accept 拒绝：severity=blocker 是红线，不可接受。改用 --reject / --human-review"; echo "===📋 END==="; exit 2; }
    [[ "$MON_MODE" == "execute" || "$EVN" -gt 0 ]] || { echo "🚫 accept 拒绝：evidence 为空，不采信无证据的完成"; echo "===📋 END==="; exit 2; }
    VERDICT=$(build_verdict accept)
    update_state ".status=\"accepted\" | .decision={kind:\"accept\",attempt_id:.run.attempt_id,launch_fingerprint:.run.launch_fingerprint,at:\"$(now_iso)\"} | .verdict=$(printf '%s' "$VERDICT" | jq -R -s '{yaml:.}')"
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
    update_state ".status=\"rejected\" | .decision={kind:\"reject\",attempt_id:.run.attempt_id,launch_fingerprint:.run.launch_fingerprint,at:\"$(now_iso)\"} | .verdict=$(printf '%s' "$VERDICT" | jq -R -s '{yaml:.}')"
    printf '%s\n' "$VERDICT" > "$OMP_TMPDIR/omp-verdict-${TASK_ID}.yaml"
    echo "↩️  REJECTED · task_id=$TASK_ID · reject_count=$REJN · next_action=$NA"
    [[ "$NA" == "stop" ]] && echo "   ⛔ reject 超限，硬终止：停循环，升级人工 / 转 cc-tmux"
    echo "   产物保留供分析: $RAW"
    ;;
  human_review)
    NA="human_review"
    VERDICT=$(build_verdict "$NA")
    update_state ".status=\"rejected\" | .human_review=true | .decision={kind:\"human_review\",attempt_id:.run.attempt_id,launch_fingerprint:.run.launch_fingerprint,at:\"$(now_iso)\"} | .verdict=$(printf '%s' "$VERDICT" | jq -R -s '{yaml:.}')"
    printf '%s\n' "$VERDICT" > "$OMP_TMPDIR/omp-verdict-${TASK_ID}.yaml"
    echo "🧑‍⚖️ HUMAN_REVIEW · task_id=$TASK_ID · 升级人工复核（不占 reject 配额）"
    echo "   产物保留: $RAW"
    ;;
esac

echo "--- Hermes verdict ---"
printf '%s\n' "$VERDICT"
echo "===📋 END==="
exit $EXITCODE
