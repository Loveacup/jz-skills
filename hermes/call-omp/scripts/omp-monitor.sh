#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-monitor.sh —— 四步③：监控 OMP 执行状态 + 双层校验输出
#
# 职责（持续监控的核心，非 fire-and-forget）：
#   · async 进行中（pid 存活）→ 报告进度（raw 大小/行数），不评判，可重复调用轮询。
#   · 完成（同步结束 / async pid 退出）→ 双层校验：
#       传输层：gate-verify --mode output（JSONL 完整 + turn_end + 内层 JSON + evidence 非空）
#       应用层：severity ∈ {nit,concern,blocker,pass}、summary 非空、退出码（同步）
#     全过 → status=reported（结论入 state.monitor，供 finish 转 verdict）；
#     任一失败 → status=rejected + 具体原因。
#   只消费 severity/summary/evidence 索引，不把上百 KB raw 打进上下文。
#
#   · --watch 模式（v0.4.0）：自动轮询循环，进度变化时输出，完成时自动裁决。
#     输出与 cc-tmux 📡 监控模板对齐（===📡 BEGIN/END=== + 距上次时长 + raw 增长）。
#     ACP 通道不配 --watch——ACP delegate_task 自带回调，完成时 Hermes 直接调单次 monitor。
#
# 参数：
#   --state <file>       状态文件（与 --task-id 二选一）
#   --task-id <id>       任务 id（自动定位状态文件）
#   --json               仅输出 JSON 报告（默认人类可读 + 末行 JSON）
#   --watch              进入轮询模式（--state 必填，RPC/Shell 专属，ACP 不支持）
#   --interval <s>       轮询间隔秒数（默认 10，仅 --watch）
#   --timeout <s>        总超时秒数（默认读 state run.max_time+60，仅 --watch）
#   --notify-on-change   进度不变时沉默输出（仅 --watch）
#   -h|--help
#
# 退出码： 0 reported / 仍在运行 · 1 结构或 severity 非法（→rejected/human_review）
#          · 2 omp 退出码非 0 / raw 缺失 · 3 参数错误 · 10 evidence 为空（→rejected）
#          · 20 --watch 超时（已自动 kill + rejected）
# stdout： 监控报告（relay）。状态文件 .monitor 字段写入结构化结论。
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SELF_DIR/lib/omp-lib.sh"
GATE="$SELF_DIR/gate"

STATE=""; TASK_ID=""; JSON_ONLY=false; WATCH=false; INTERVAL=10; WATCH_TIMEOUT=0; NOTIFY_CHANGE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state)   STATE="$2"; shift 2 ;;
    --task-id) TASK_ID="$2"; shift 2 ;;
    --json)    JSON_ONLY=true; shift ;;
    --watch)   WATCH=true; shift ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --timeout) WATCH_TIMEOUT="$2"; shift 2 ;;
    --notify-on-change) NOTIFY_CHANGE=true; shift ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "omp-monitor: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ -z "$STATE" && -n "$TASK_ID" ]] && STATE="$(state_path "$TASK_ID")"
[[ -n "$STATE" && -r "$STATE" ]] || { echo "omp-monitor: 读不到状态文件（--state/--task-id）" >&2; exit 3; }

TASK_ID=$(jq -r '.task_id' "$STATE")
STATUS=$(jq -r '.status' "$STATE")
RAW=$(jq -r '.run.raw_output // empty' "$STATE")
PID=$(jq -r '.run.pid // empty' "$STATE")
EC=$(jq -r '.run.exit_code // empty' "$STATE")
CHANNEL_USED=$(jq -r '.run.channel_used // ""' "$STATE")
RPC_PID=$(jq -r '.run.rpc_pid // empty' "$STATE")
TSL=$(jq -r '.run.turn_start_line // 0' "$STATE")

update_state() { local f="$1"; local s; s=$(jq "$f | .updated_at=\"$(now_iso)\"" "$STATE"); printf '%s' "$s" | atomic_write "$STATE"; }
report_line() { $JSON_ONLY || echo "$1"; }

[[ -n "$RAW" ]] || { echo "omp-monitor: 状态无 raw_output（尚未 send？status=${STATUS}）" >&2; exit 2; }


# ═══════════════════════════════════════════════
# --watch 轮询模式（RPC/Shell 专属）
# ACP 不支持（delegate_task 自带回调，完成时直接调单次 monitor）
# ═══════════════════════════════════════════════
if $WATCH; then
  [[ "$CHANNEL_USED" == "acp" ]] && { echo "omp-monitor: --watch 不支持 ACP 通道（delegate_task 自带回调）" >&2; exit 3; }
  [[ "$INTERVAL" =~ ^[1-9][0-9]*$ ]] || { echo "omp-monitor: --interval 须为正整数" >&2; exit 3; }

  # 超时默认：读 state 的 run.max_time + 60s（cover perl alarm +30s + buffer）
  if [[ "$WATCH_TIMEOUT" -le 0 ]]; then
    MT=$(jq -r '.run.max_time // 300' "$STATE")
    [[ "$MT" =~ ^[1-9][0-9]*$ ]] || MT=300
    WATCH_TIMEOUT=$((MT + 60))
  fi

  START_TS=$(date +%s); LAST_TS=$START_TS
  LAST_SZ=-1; LAST_LN=-1
  SEQ=0

  echo "===📡 BEGIN omp-monitor --watch (relay verbatim)==="
  echo "📡 watch 启动 · task_id=$TASK_ID · channel=$CHANNEL_USED · interval=${INTERVAL}s · timeout=${WATCH_TIMEOUT}s"

  while true; do
    # 超时检查
    NOW_TS=$(date +%s)
    ELAPSED=$((NOW_TS - START_TS))
    if [[ $ELAPSED -ge $WATCH_TIMEOUT ]]; then
      echo "===📡 BEGIN timeout==="
      echo "⏰ 超时 · ${ELAPSED}s / ${WATCH_TIMEOUT}s"
      echo "===📡 END==="
      # 主动 kill + reject
      RPID=$(jq -r '.run.rpc_pid // empty' "$STATE"); [[ -n "$RPID" ]] && kill "$RPID" 2>/dev/null
      SPID=$(jq -r '.run.pid // empty' "$STATE"); [[ -n "$SPID" ]] && kill "$SPID" 2>/dev/null
      update_state ".status=\"rejected\" | .monitor={checked_at:\"$(now_iso)\",issues:[\"--watch timeout ${WATCH_TIMEOUT}s\"]}"
      echo "===📡 BEGIN omp-monitor (relay verbatim)==="
      echo "📡 监控完成 · task_id=$TASK_ID · → status=rejected"
      echo "   ⚠️ 问题: --watch 超时 ${WATCH_TIMEOUT}s"
      echo "   下一步: omp-finish.sh --state $STATE --reject"
      echo "===📡 END==="
      exit 20
    fi

    # 单次检查
    OUT=$("$0" --state "$STATE" --json 2>&1); RC=$?
    PHASE=$(echo "$OUT" | jq -r '.phase // "unknown"' 2>/dev/null)
    SZ=$(echo "$OUT" | jq -r '.raw_bytes // 0' 2>/dev/null); [[ "$SZ" =~ ^[0-9]+$ ]] || SZ=0
    LN=$(echo "$OUT" | jq -r '.raw_lines // 0' 2>/dev/null); [[ "$LN" =~ ^[0-9]+$ ]] || LN=0

    # 判断阶段
    if [[ "$PHASE" != "running" ]]; then
      # 完成/失败 → 重新输出完整报告（非 --json，人类可读）
      "$0" --state "$STATE" 2>/dev/null
      echo "===📡 END==="
      exit $RC
    fi

    # 仍在运行：进度变化检查
    DELTA=$((NOW_TS - LAST_TS)); LAST_TS=$NOW_TS
    SEQ=$((SEQ + 1))
    if ! $NOTIFY_CHANGE || [[ "$SZ" != "$LAST_SZ" || "$LN" != "$LAST_LN" ]]; then
      echo "📡 #${SEQ} [距上次 ${DELTA}s] ${CHANNEL_USED} 运行中 · raw ${SZ}B/${LN}行 · interval=${INTERVAL}s"
      LAST_SZ=$SZ; LAST_LN=$LN
    fi

    # 确定要监控的 pid
    MPID=""; [[ "$CHANNEL_USED" == "rpc" ]] && MPID=$(jq -r '.run.rpc_pid // empty' "$STATE") || MPID=$(jq -r '.run.pid // empty' "$STATE")
    echo "   └ 轮询: ${INTERVAL}s 后重查 · 干预: kill ${MPID:-<pid>}"

    sleep "$INTERVAL"
  done
  # unreachable — watch loop covers all paths
fi


# ── RPC 通道：daemon 心跳 + 本轮 turn_end（turn_start_line marker 只看本轮）──
if [[ "$CHANNEL_USED" == "rpc" && "$STATUS" == "running" ]]; then
  if rpc_turn_done "$RAW" "$TSL"; then
    : # 本轮已收尾 → 落入下方完成校验（双层解析与 shell 通用）
  elif rpc_daemon_alive "$RPC_PID"; then
    SZ=0; LN=0
    if [[ -f "$RAW" ]]; then SZ=$(wc -c <"$RAW" | tr -d ' '); LN=$(wc -l <"$RAW" | tr -d ' '); fi
    report_line "===📡 BEGIN omp-monitor (relay verbatim)==="
    report_line "⏳ RPC 仍在运行 · task_id=$TASK_ID · daemon pid=$RPC_PID · raw ${SZ}B / ${LN} 行"
    report_line "   继续轮询: omp-monitor.sh --state $STATE   · 干预: kill $RPC_PID"
    report_line "===📡 END==="
    printf '{"task_id":"%s","phase":"running","channel":"rpc","pid":%s,"raw_bytes":%s,"raw_lines":%s}\n' "$TASK_ID" "$RPC_PID" "$SZ" "$LN"
    exit 0
  else
    update_state ".status=\"rejected\" | .monitor={checked_at:\"$(now_iso)\",issues:[\"rpc daemon 已退出且本轮无 turn_end（崩溃/超时）\"]}"
    echo "🚫 omp-monitor: rpc daemon 死亡且本轮无 turn_end → status=rejected" >&2
    exit 2
  fi
fi

# ── Shell async 进行中：pid 存活 → 只报进度，不评判 ──
if [[ -n "$PID" && "$STATUS" == "running" ]] && kill -0 "$PID" 2>/dev/null; then
  # 用 wc（空文件 exit 0）而非 grep -c（空文件 exit 1 + || echo 会双输出污染 JSON）
  SZ=0; LN=0
  if [[ -f "$RAW" ]]; then SZ=$(wc -c <"$RAW" | tr -d ' '); LN=$(wc -l <"$RAW" | tr -d ' '); fi
  report_line "===📡 BEGIN omp-monitor (relay verbatim)==="
  report_line "⏳ OMP 仍在运行 · task_id=$TASK_ID · pid=$PID · raw ${SZ}B / ${LN} 行"
  report_line "   继续轮询: omp-monitor.sh --state $STATE   · 干预: kill $PID"
  report_line "===📡 END==="
  printf '{"task_id":"%s","phase":"running","pid":%s,"raw_bytes":%s,"raw_lines":%s}\n' "$TASK_ID" "$PID" "$SZ" "$LN"
  exit 0
fi

# ── 完成：raw 须存在非空 ──
if [[ ! -s "$RAW" ]]; then
  update_state ".status=\"rejected\" | .monitor={checked_at:\"$(now_iso)\",issues:[\"raw 缺失或空\"]}"
  echo "🚫 omp-monitor: raw 缺失/空 → status=rejected" >&2
  exit 2
fi

ISSUES=(); REJECT=false; EXITCODE=0

# ── 传输层 + 应用层①②③：复用 gate-verify --mode output ──
set +e
GV_OUT=$(bash "$GATE/gate-verify.sh" --mode output --file "$RAW" 2>/dev/null); GV_RC=$?
set -e
if [[ $GV_RC -eq 10 ]]; then
  ISSUES+=("evidence 为空（gate-verify exit 10）"); REJECT=true; EXITCODE=10
elif [[ $GV_RC -ne 0 ]]; then
  ISSUES+=("输出结构不合格: $(echo "$GV_OUT" | jq -r '.reason' 2>/dev/null || echo "$GV_OUT")"); REJECT=true; EXITCODE=1
fi

# ── 提取内层审计 JSON（用于 severity/summary 校验 + 存档供 finish）──
FINAL=$(jsonl_final_text "$RAW")
INNER=$(extract_inner_json "$FINAL")
SEV=""; SUMMARY=""; EVN=0; SEV_VALID=false
if [[ -n "$INNER" ]] && inner_json_valid "$INNER"; then
  SEV=$(printf '%s' "$INNER" | jq -r '.severity // ""')
  SUMMARY=$(printf '%s' "$INNER" | jq -r '.summary // ""')
  EVN=$(printf '%s' "$INNER" | jq -r 'if (.evidence|type)=="array" then (.evidence|length) else 0 end')
  case "$SEV" in nit|concern|blocker|pass) SEV_VALID=true ;; *) SEV_VALID=false ;; esac
fi
# 应用层④：severity 合法值
if [[ "$REJECT" == false && "$SEV_VALID" == false ]]; then
  ISSUES+=("severity 非法值 '$SEV'（须 nit|concern|blocker|pass）→ human_review"); REJECT=true; EXITCODE=1
fi
# 应用层⑤：summary 非空
if [[ "$REJECT" == false && -z "$SUMMARY" ]]; then
  ISSUES+=("缺 summary 结论摘要"); REJECT=true; EXITCODE=1
fi

# ── stopReason / 退出码（同步有 EC；async 用 turn_end 兜底）──
STOP=$(jsonl_stop_reason "$RAW"); [[ -z "$STOP" ]] && STOP="unknown"
if [[ -n "$EC" && "$EC" != "null" && "$EC" -ne 0 ]]; then
  ISSUES+=("omp 退出码非 0（${EC}）"); REJECT=true; [[ $EXITCODE -eq 0 ]] && EXITCODE=2
fi

# ── 写监控报告到 state ──
# 空数组直接 []（不能走 grep 管道：空时 grep exit 1 触发 pipefail，|| echo 会追加成 "[]\n[]"）
if [[ ${#ISSUES[@]} -eq 0 ]]; then ISSUES_J='[]'
else ISSUES_J=$(printf '%s\n' "${ISSUES[@]}" | jq -R . | jq -sc .); fi
MON=$(jq -n --arg now "$(now_iso)" --arg sev "$SEV" --arg sum "$SUMMARY" \
   --argjson evn "${EVN:-0}" --arg stop "$STOP" --argjson sv "$SEV_VALID" \
   --argjson issues "$ISSUES_J" --argjson inner "${INNER:-null}" \
   '{checked_at:$now,severity:$sev,severity_valid:$sv,summary:$sum,evidence_count:$evn,stop_reason:$stop,issues:$issues,inner:$inner}' 2>/dev/null \
   || jq -n --arg now "$(now_iso)" --argjson issues "$ISSUES_J" '{checked_at:$now,issues:$issues,inner:null}')

if $REJECT; then
  update_state ".status=\"rejected\" | .monitor=$MON"
  NEWSTATUS="rejected"
else
  update_state ".status=\"reported\" | .monitor=$MON"
  NEWSTATUS="reported"
fi

# ── 输出报告 ──
if ! $JSON_ONLY; then
  echo "===📡 BEGIN omp-monitor (relay verbatim)==="
  echo "📡 监控完成 · task_id=$TASK_ID · → status=$NEWSTATUS"
  echo "   severity : ${SEV:-?}（合法=${SEV_VALID}）   evidence: ${EVN} 条   stopReason: $STOP"
  [[ -n "$SUMMARY" ]] && echo "   summary  : ${SUMMARY:0:160}"
  if [[ ${#ISSUES[@]} -gt 0 && -n "${ISSUES[0]:-}" ]]; then
    echo "   ⚠️ 问题:"; for i in "${ISSUES[@]}"; do [[ -n "$i" ]] && echo "     - $i"; done
  fi
  if [[ "$NEWSTATUS" == "reported" ]]; then
    echo "   下一步   : omp-finish.sh --state $STATE --accept|--reject|--human-review"
    [[ "$SEV" == "blocker" ]] && echo "   ⛔ severity=blocker → 不应 accept；按 evidence 决定 reject/转 cc-tmux 修复"
  else
    echo "   下一步   : 已 rejected。修复委派包后重 start，或转人工/cc-tmux"
  fi
  echo "===📡 END==="
fi
printf '{"task_id":"%s","phase":"%s","severity":"%s","severity_valid":%s,"evidence_count":%s,"stop_reason":"%s","issues":%s}\n' \
  "$TASK_ID" "$NEWSTATUS" "$SEV" "$SEV_VALID" "${EVN:-0}" "$STOP" "$ISSUES_J"
exit $EXITCODE
