#!/usr/bin/env bash
# Authenticated execute_v1 cancellation request. Never signals a PID/PGID.
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SELF_DIR/lib/omp-lib.sh"

STATE=""; EXPECT_ATTEMPT=""; EXPECT_FP=""; REASON=""; TIMEOUT=10
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state) STATE="$2"; shift 2 ;;
    --attempt-id) EXPECT_ATTEMPT="$2"; shift 2 ;;
    --launch-fingerprint) EXPECT_FP="$2"; shift 2 ;;
    --reason) REASON="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    -h|--help) sed -n '1,28p' "$0"; exit 0 ;;
    *) echo "omp-stop: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ -n "$STATE" && -r "$STATE" ]] || { echo "omp-stop: 读不到 --state" >&2; exit 3; }
validate_attempt_id "$EXPECT_ATTEMPT" || { echo "omp-stop: --attempt-id 须为 UUIDv4" >&2; exit 3; }
[[ "$EXPECT_FP" =~ ^[0-9a-f]{64}$ ]] || { echo "omp-stop: --launch-fingerprint 须为小写 SHA-256" >&2; exit 3; }
[[ -n "$REASON" ]] || { echo "omp-stop: --reason 不得为空" >&2; exit 3; }
[[ "$TIMEOUT" =~ ^([0-9]+)(\.[0-9]+)?$ ]] || { echo "omp-stop: --timeout 须为正数" >&2; exit 3; }
awk -v t="$TIMEOUT" 'BEGIN{exit !(t>0)}' || { echo "omp-stop: --timeout 须大于 0" >&2; exit 3; }

TASK_ID=$(jq -r '.task_id // empty' "$STATE")
require_task_id "$TASK_ID" || exit 3
EXPECTED_STATE="$(state_path "$TASK_ID")"
[[ "$STATE" == "$EXPECTED_STATE" ]] || { echo "omp-stop: state 非规范 task-id 路径" >&2; exit 3; }
trap 'lifecycle_lock_release 2>/dev/null || true' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
if ! lifecycle_lock_acquire "$TASK_ID"; then
  echo "omp-stop: 任务 $TASK_ID 生命周期锁被占用或遗留；未写取消请求" >&2
  exit 2
fi

# Re-authenticate expected identity under exclusion. A stale caller can never
# cancel a newer attempt because no PID-based fallback exists.
CUR_ATTEMPT=$(jq -r '.run.attempt_id // empty' "$STATE")
CUR_FP=$(jq -r '.run.launch_fingerprint // empty' "$STATE")
EXEC_SUP=$(jq -r '.run.execution_supervised // false' "$STATE")
CAPTURE=$(jq -r '.run.capture_mode // empty' "$STATE")
RSTATE="$(resource_state_path "$TASK_ID")"
PIDS="$(pid_store_path "$TASK_ID")"
CONTROL="$(control_file_path "$TASK_ID")"
RAW="$(raw_path "$TASK_ID")"
BOUND=$(jq -r --arg rs "$RSTATE" --arg ps "$PIDS" --arg cf "$CONTROL" --arg ro "$RAW" '
  (.run.resource_state==$rs and .run.pid_store==$ps and .run.control_file==$cf and .run.raw_output==$ro)' "$STATE" 2>/dev/null || echo false)
if [[ "$EXEC_SUP" != "true" || "$CAPTURE" != "execute_v1" || "$BOUND" != "true" ]]; then
  echo "omp-stop: 当前 state 不是规范 execute_v1 supervised attempt" >&2
  exit 2
fi
if [[ "$CUR_ATTEMPT" != "$EXPECT_ATTEMPT" || "$CUR_FP" != "$EXPECT_FP" ]]; then
  echo "omp-stop: expected identity 与当前 attempt 不匹配；拒绝 stale stop" >&2
  exit 2
fi

for _f in "$RSTATE" "$PIDS" "$CONTROL"; do
  [[ ! -L "$_f" ]] || { echo "omp-stop: canonical sidecar 为 symlink，拒绝" >&2; exit 2; }
  [[ ! -e "$_f" || -f "$_f" ]] || { echo "omp-stop: canonical sidecar 非普通文件，拒绝" >&2; exit 2; }
done

load_matching_terminal_receipt() {
  local ci clean receipt_status
  [[ -f "$RSTATE" && ! -L "$RSTATE" && -f "$PIDS" && ! -L "$PIDS" ]] || return 1
  if ! jq -e --arg tid "$TASK_ID" --arg aid "$EXPECT_ATTEMPT" \
      --arg fp "$EXPECT_FP" --arg sf "$RSTATE" --arg ro "$RAW" \
      --arg ps "$PIDS" --arg cf "$CONTROL" '
      .schema=="call-omp-resource-supervisor.v2" and .capture_mode=="execute_v1" and
      .task_id==$tid and .attempt_id==$aid and .launch_fingerprint==$fp and
      .state_file==$sf and .raw_output==$ro and .control_file==$cf and
      .run.pid_store==$ps and ((.status=="reported") or (.status=="rejected")) and
      .cleanup_confirmed==true and (.terminal_reason|type)=="string" and
      (.child_identity|type)=="object" and .exit_code==.worker_exit_code and
      ((.worker_exit_code==null) or
        ((.worker_exit_code|type)=="number" and .worker_exit_code==(.worker_exit_code|floor))) and
      ((.supervisor_exit_code|type)=="number" and
        .supervisor_exit_code==(.supervisor_exit_code|floor))' "$RSTATE" >/dev/null 2>&1; then
    return 1
  fi
  RECEIPT=$(cat "$RSTATE") || return 1
  ci=$(printf '%s' "$RECEIPT" | jq -c '.child_identity') || return 1
  clean=$(printf '%s' "$RECEIPT" | jq -c '.cleanup_confirmed') || return 1
  receipt_status=$(printf '%s' "$RECEIPT" | jq -r '.status') || return 1
  jq -e --arg tid "$TASK_ID" --arg aid "$EXPECT_ATTEMPT" \
    --arg fp "$EXPECT_FP" --arg sf "$RSTATE" --arg ro "$RAW" \
    --arg ps "$PIDS" --arg cf "$CONTROL" --arg st "$receipt_status" \
    --argjson clean "$clean" --argjson ci "$ci" '
    .schema=="call-omp-execute-identity.v1" and .capture_mode=="execute_v1" and
    .task_id==$tid and .attempt_id==$aid and .launch_fingerprint==$fp and
    .state_file==$sf and .raw_output==$ro and .pid_store==$ps and .control_file==$cf and
    .status==$st and .cleanup_confirmed==$clean and .child_identity==$ci' \
    "$PIDS" >/dev/null 2>&1
}

# Repeated stop on an accepted, authenticated clean terminal attempt is an
# idempotent observation, never a cancellation rewrite.
MAIN_STATUS=$(jq -r '.status // empty' "$STATE")
if [[ "$MAIN_STATUS" == "accepted" ]]; then
  if [[ "$(jq -r '.run.cancel_requested // false' "$STATE")" != "true" && ! -e "$CONTROL" ]] \
     && load_matching_terminal_receipt \
     && printf '%s' "$RECEIPT" | jq -e '
          .status=="reported" and .worker_exit_code==0 and .exit_code==0 and
          .supervisor_exit_code==0 and .cleanup_confirmed==true' >/dev/null 2>&1; then
    echo "task_id=$TASK_ID attempt_id=$EXPECT_ATTEMPT status=accepted cleanup_confirmed=true already_terminal=true"
    exit 0
  fi
  echo "omp-stop: accepted state 缺少匹配的 clean terminal proof；拒绝改写历史" >&2
  exit 2
fi

REQUEST=$(jq -cn --arg tid "$TASK_ID" --arg aid "$EXPECT_ATTEMPT" \
  --arg fp "$EXPECT_FP" --arg reason "$REASON" \
  '{schema:"call-omp-cancel.v1",task_id:$tid,attempt_id:$aid,launch_fingerprint:$fp,reason:$reason}')
if [[ -e "$CONTROL" ]]; then
  if ! jq -e --arg tid "$TASK_ID" --arg aid "$EXPECT_ATTEMPT" --arg fp "$EXPECT_FP" '
      .schema=="call-omp-cancel.v1" and .task_id==$tid and
      .attempt_id==$aid and .launch_fingerprint==$fp and (.reason|type)=="string"' \
      "$CONTROL" >/dev/null 2>&1; then
    echo "omp-stop: 已有 control request 身份不匹配/非法；拒绝覆盖 immutable request" >&2
    exit 2
  fi
else
  printf '%s\n' "$REQUEST" | atomic_write "$CONTROL"
fi

update_cancel_state() {
  local filter="$1" next
  next=$(jq "$filter | .updated_at=\"$(now_iso)\"" "$STATE")
  printf '%s\n' "$next" | atomic_write "$STATE"
}
REASON_JSON=$(printf '%s' "$REASON" | jq -R -s '.')
update_cancel_state ".run.cancel_requested=true |
  .run.cancel_reason=$REASON_JSON |
  .run.cancel_requested_at=\"$(now_iso)\" | .run.cleanup_confirmed=false"

STEPS=$(awk -v t="$TIMEOUT" 'BEGIN{n=int(t*10+0.999); if(n<1)n=1; print n}')
i=0
while [[ "$i" -lt "$STEPS" ]]; do
  if load_matching_terminal_receipt; then
    RSTATUS=$(printf '%s' "$RECEIPT" | jq -r '.status')
    WORKER=$(printf '%s' "$RECEIPT" | jq -c '.worker_exit_code')
    SUP_EXIT=$(printf '%s' "$RECEIPT" | jq -c '.supervisor_exit_code')
    TERM=$(printf '%s' "$RECEIPT" | jq -c '.terminal_reason')
    RECEIPT_SUBSET=$(printf '%s' "$RECEIPT" | jq -c '{schema,status,task_id,attempt_id,launch_fingerprint,worker_exit_code,supervisor_exit_code,terminal_reason,cleanup_confirmed,child_identity}')
    update_cancel_state ".status=\"rejected\" | .run.exit_code=$WORKER |
      .run.worker_exit_code=$WORKER | .run.supervisor_exit_code=$SUP_EXIT |
      .run.terminal_reason=$TERM | .run.cleanup_confirmed=true |
      .monitor={checked_at:\"$(now_iso)\",issues:[\"execute_v1 cancellation requested; terminal cleanup confirmed\"],resource:$RECEIPT_SUBSET}"
    if [[ "$RSTATUS" == "reported" ]]; then
      echo "omp-stop: cancellation 已请求，但 receipt 为 reported；主状态保持 rejected（不得转成功）" >&2
      exit 2
    fi
    echo "task_id=$TASK_ID attempt_id=$EXPECT_ATTEMPT status=rejected cleanup_confirmed=true"
    exit 0
  fi
  sleep 0.1
  i=$((i + 1))
done

# Timeout is unknown cleanup, not a stopped claim. start will refuse replacement
# until a later matching terminal receipt proves cleanup.
update_cancel_state ".status=\"rejected\" | .run.cleanup_confirmed=false |
  .run.terminal_reason=\"cancel_cleanup_unknown\" |
  .monitor={checked_at:\"$(now_iso)\",issues:[\"execute_v1 cancellation requested; cleanup unknown after bounded wait\"]}"
echo "omp-stop: bounded wait 到期；cleanup unknown（未发送任何 PID/PGID signal）" >&2
exit 2
