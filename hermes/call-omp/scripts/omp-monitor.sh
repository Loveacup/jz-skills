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

STATE=""; TASK_ID=""; JSON_ONLY=false; WATCH=false; INTERVAL=10; WATCH_TIMEOUT=0; NOTIFY_CHANGE=false; MONITOR_MODE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state)   STATE="$2"; shift 2 ;;
    --task-id) TASK_ID="$2"; shift 2 ;;
    --json)    JSON_ONLY=true; shift ;;
    --mode)    MONITOR_MODE="$2"; shift 2 ;;
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
require_task_id "$TASK_ID" || exit 3
# 自动检测 mode（用于 execute 跳过 JSON 校验）
if [[ -z "$MONITOR_MODE" ]]; then
  MONITOR_MODE=$(jq -r '.package.mode // ""' "$STATE")
  MONITOR_MODE="${MONITOR_MODE%%:*}"
fi
STATUS=$(jq -r '.status' "$STATE")
RAW=$(jq -r '.run.raw_output // empty' "$STATE")
EXPECTED_RAW=$(raw_path "$TASK_ID")
[[ -z "$RAW" || "$RAW" == "$EXPECTED_RAW" ]] || { echo "omp-monitor: state raw_output 非规范路径" >&2; exit 3; }
RAW="$EXPECTED_RAW"
PID=$(jq -r '.run.pid // empty' "$STATE")
EC=$(jq -r '.run.exit_code // empty' "$STATE")
RUN_MODE=$(jq -r '.run.mode // empty' "$STATE")
CHANNEL_USED=$(jq -r '.run.channel_used // ""' "$STATE")
RPC_PID=$(jq -r '.run.rpc_pid // empty' "$STATE")
TSL=$(jq -r '.run.turn_start_line // 0' "$STATE")
# bundle_only Shell 审计经资源监督器运行时 send 落此标记；仅此时才走资源终态检测。
RESOURCE_SUPERVISED=$(jq -r '.run.resource_supervised // false' "$STATE")

update_state() { local f="$1"; local s; s=$(jq "$f | .updated_at=\"$(now_iso)\"" "$STATE"); printf '%s' "$s" | atomic_write "$STATE"; }
report_line() { $JSON_ONLY || echo "$1"; }
# P2B S2：verdict_v1 capture 认证通过后的有界 capture 元数据（纯数值/布尔/hash 子集）。
# 全程默认空——仅 authenticated verdict_v1 reported 路径填充；非监督/legacy 运行恒空。
CAPTURE_META=""
# 文件 SHA-256（与监督器 hashlib.sha256 同形，小写 hex）；shasum 优先，sha256sum 兜底。
sha256_of() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'; else sha256sum "$1" | awk '{print $1}'; fi; }

[[ -n "$RAW" ]] || { echo "omp-monitor: 状态无 raw_output（尚未 send？status=${STATUS}）" >&2; exit 2; }

# ═══ P2B S2r1 · 主状态 = capture 迁移权威（先于资源块 / legacy raw 解析）═══════════
# main.run.capture_mode 是迁移权威，全流程最先裁决，杜绝「main 已迁移 verdict_v1 却因
# 资源侧缺失/异常被静默降级为 legacy」的跨状态降级洞：
#   · nonempty 且非 verdict_v1  → 未知 capture 模式，立即 fail-closed（不静默当 legacy）。
#   · verdict_v1 但非 resource_supervised → 无监督器无法认证 capture，fail-closed。
# 消息恒为静态串（不回显 state 内可控值），仅落有界 issue，绝不含 raw/diag 正文/argv。
M_CAPTURE_MODE=$(jq -r '.run.capture_mode // ""' "$STATE")
if [[ -n "$M_CAPTURE_MODE" && "$M_CAPTURE_MODE" != "verdict_v1" ]]; then
  update_state ".status=\"rejected\" | .monitor={checked_at:\"$(now_iso)\",issues:[\"未知 main.run.capture_mode（仅接受空或 verdict_v1）\"]}"
  echo "🚫 omp-monitor: 未知 main.run.capture_mode → status=rejected（fail-closed）" >&2; exit 2
fi
if [[ "$M_CAPTURE_MODE" == "verdict_v1" && "$RESOURCE_SUPERVISED" != "true" ]]; then
  update_state ".status=\"rejected\" | .monitor={checked_at:\"$(now_iso)\",issues:[\"main.run.capture_mode=verdict_v1 但非 resource_supervised，无法认证 capture\"]}"
  echo "🚫 omp-monitor: verdict_v1 需 resource_supervised → status=rejected（fail-closed）" >&2; exit 2
fi


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
      # 主动 kill + reject —— 但资源监督进程组不由 monitor kill：
      # 监督器（omp-resource-supervisor.py）自持 pgid（pid_store 规范 sidecar）并
      # 已 enforce raw_cap/rate_fuse 的安全收束，盲 kill wrapper pid 既不干净也越界。
      # 故 resource_supervised 时只 fail-closed 主状态，不引入 kill $pid（走既有安全路径）。
      if [[ "$RESOURCE_SUPERVISED" != "true" ]]; then
        RPID=$(jq -r '.run.rpc_pid // empty' "$STATE"); [[ -n "$RPID" ]] && kill "$RPID" 2>/dev/null
        SPID=$(jq -r '.run.pid // empty' "$STATE"); [[ -n "$SPID" ]] && kill "$SPID" 2>/dev/null
      else
        echo "🛡  --watch 超时：resource_supervised 运行由监督器自持 pgroup，monitor 不 kill wrapper pid" >&2
      fi
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


# ═══════════════════════════════════════════════
# 资源监督器终态检测（bundle_only Shell 审计专属）
# 先于常规 running/完成 / JSONL 判决解析：已【认证】的资源监督终态必须在
# 【主 call-omp 状态机】fail-closed，不得进入 raw 解析或 verdict 抽取。
# 只认 task-id 规范 sidecar（禁止跟随任意路径）；非监督运行完全跳过本块（语义不变）。
# ═══════════════════════════════════════════════
if [[ "$RESOURCE_SUPERVISED" == "true" ]]; then
  R_STATE=$(jq -r '.run.resource_state // empty' "$STATE")
  R_PIDS=$(jq -r '.run.pid_store // empty' "$STATE")
  EXP_RSTATE="$(resource_state_path "$TASK_ID")"
  EXP_RPIDS="$(pid_store_path "$TASK_ID")"

  # ── 有界化助手（P0B3R2·D）：任意字符串截断到 ≤512 codepoints + 确定性截断标记；
  #    若原文含 containment_failure 但落在界外，显式补一个有界 containment_failure 标记（不软化）。
  bound512() { printf '%s' "${1:-}" | jq -Rrs --argjson max 512 '
      def mk: "…[truncated]";
      if (length <= $max) then .
      else (.[0:($max - (mk|length))]) as $h
        | if ((test("containment_failure")) and (($h|test("containment_failure"))|not))
          then (.[0:($max - 32)]) + " containment_failure" + mk
          else $h + mk end
      end' 2>/dev/null; }
  # ── fail-closed 助手：把（有界化后的）issue JSON-encode 落主状态 rejected ──
  reject_res() { local msg ij; msg=$(bound512 "$1"); ij=$(jq -Rn --arg s "$msg" '$s')
    update_state ".status=\"rejected\" | .monitor={checked_at:\"$(now_iso)\",issues:[$ij]}"
    echo "🚫 omp-monitor: $msg → status=rejected（fail-closed）" >&2; }
  # ── running（starting/pre-sidecar）统一输出：只报边界化 raw_bytes/raw_lines，不解析 raw ──
  emit_running() { # $1=阶段标签
    report_line "===📡 BEGIN omp-monitor (relay verbatim)==="
    report_line "⏳ 资源监督运行中（$1）· task_id=$TASK_ID · raw ${R_RB}B / ${R_RL} 行（监督器边界计数）"
    report_line "   继续轮询: omp-monitor.sh --state $STATE"
    report_line "===📡 END==="
    printf '{"task_id":"%s","phase":"running","channel":"shell","resource_supervised":true,"raw_bytes":%s,"raw_lines":%s}\n' "$TASK_ID" "$R_RB" "$R_RL"; }
  # ── 有界 forensic 子集（P0B3R2·D）：白名单字段 only，绝不含 argv / raw 正文 / raw tail / 未知嵌套；
  #    reason 用调用方传入的【有界】串；rate_fuse 仅取 typed 标量子集。$1=有界 reason。
  res_subset() { # $1=bounded reason
    jq -c --arg br "$1" '{
        schema, status, reason: $br,
        raw_bytes, raw_sha256: (.raw_sha256 // ""), raw_tail_bytes,
        child_identity: {pid: .child_identity.pid, pgid: .child_identity.pgid, session_id: .child_identity.session_id},
        run: {exit_code: .run.exit_code},
        rate_fuse: (if ((.rate_fuse|type)=="object") then {
            enabled:          (.rate_fuse.enabled          | if type=="boolean" then . else false end),
            window_bytes:     (.rate_fuse.window_bytes     | if type=="number"  then . else null  end),
            window_seconds:   (.rate_fuse.window_seconds   | if type=="number"  then . else null  end),
            fuse_windows:     (.rate_fuse.fuse_windows     | if type=="number"  then . else null  end),
            consecutive_over: (.rate_fuse.consecutive_over | if type=="number"  then . else null  end)
          } else null end)
      }' "$R_STATE" 2>/dev/null || echo null; }

  # ═══ P0B3R2·① 路径核对：resource_state / pid_store 必须等于规范 task-id 助手路径 ═══
  if [[ "$R_STATE" != "$EXP_RSTATE" || "$R_PIDS" != "$EXP_RPIDS" ]]; then
    reject_res "resource sidecar 路径非规范（疑似伪造/越权），拒绝跟随: resource_state=$R_STATE pid_store=$R_PIDS"; exit 2
  fi
  # ═══ P0B3R2·A 文件系统安全：三条 canonical 路径都不得是 symlink；存在时必须是普通文件（不跟随）═══
  for _f in "$R_STATE" "$R_PIDS" "$RAW"; do
    if [[ -L "$_f" ]]; then reject_res "canonical 路径为 symlink，拒绝跟随: $_f"; exit 2; fi
    if [[ -e "$_f" && ! -f "$_f" ]]; then reject_res "canonical 路径非普通文件: $_f"; exit 2; fi
  done
  # resource-state 必须存在为普通文件、可读、合法 JSON 对象（不可读/非法 → fail-closed）。
  if [[ ! -f "$R_STATE" || ! -r "$R_STATE" ]] || ! jq -e 'type=="object"' "$R_STATE" >/dev/null 2>&1; then
    reject_res "resource-state 缺失/不可读/非法 JSON 对象: $R_STATE"; exit 2
  fi
  # ═══ P0B3R2·B v1 绑定 + 形状：单次 jq 全量校验，首个失败字段作 fail-closed 原因 ═══
  SHAPE_ERR=$(jq -r --arg tid "$TASK_ID" --arg sf "$EXP_RSTATE" --arg ro "$RAW" --arg ps "$EXP_RPIDS" '
      def nnint: (type=="number" and . == floor and . >= 0);
      def idnull: (.==null or (type=="number" and .>0 and . == floor));
      (.status // null) as $st
      | (["starting","reported","resource_rejected","rejected"]) as $enum
      | if   (.schema != "call-omp-resource-supervisor.v1") then "schema"
        elif (.task_id != $tid) then "task_id"
        elif (.state_file != $sf) then "state_file"
        elif (.raw_output != $ro) then "raw_output"
        elif ((.run|type) != "object") then "run_obj"
        elif (.run.pid_store != $ps) then "run.pid_store"
        elif (($enum|index($st))==null) then "status_enum"
        elif ((.raw_bytes)      | nnint | not) then "raw_bytes"
        elif ((.raw_lines)      | nnint | not) then "raw_lines"
        elif ((.raw_tail_bytes) | nnint | not) then "raw_tail_bytes"
        elif (((.raw_sha256 // "")) | ((.=="") or test("^[0-9a-f]{64}$")) | not) then "raw_sha256"
        elif ((.reason|type) != "string") then "reason_type"
        elif ((.run.exit_code != null) and (((.run.exit_code|type)!="number") or (.run.exit_code != (.run.exit_code|floor)))) then "exit_code_type"
        elif ((($st == "reported") or ($st == "resource_rejected")) and (.run.exit_code == null)) then "exit_code_terminal_null"
        elif ((.child_identity|type) != "object") then "child_identity_obj"
        elif ((.child_identity.pid)        | idnull | not) then "ci_pid"
        elif ((.child_identity.pgid)       | idnull | not) then "ci_pgid"
        elif ((.child_identity.session_id) | idnull | not) then "ci_session"
        elif ((.child_identity.argv|type)  != "array") then "ci_argv"
        else "" end' "$R_STATE" 2>/dev/null || echo "jq_error")
  if [[ -n "$SHAPE_ERR" ]]; then
    reject_res "resource-state 形状/绑定校验失败（${SHAPE_ERR}）"; exit 2
  fi

  # 形状已保证类型/绑定，安全读取。
  R_STATUS=$(jq -r '.status' "$R_STATE")
  R_RB=$(jq -r '.raw_bytes' "$R_STATE")
  R_RL=$(jq -r '.raw_lines' "$R_STATE")
  R_REASON=$(jq -r '.reason' "$R_STATE")
  R_EC=$(jq -r '.run.exit_code // empty' "$R_STATE")
  CI_PID=$(jq -r '.child_identity.pid'        "$R_STATE")   # "null" 或数字
  CI_PGID=$(jq -r '.child_identity.pgid'      "$R_STATE")
  CI_SID=$(jq -r '.child_identity.session_id' "$R_STATE")
  CI_POPULATED=false; [[ "$CI_PID" != "null" ]] && CI_POPULATED=true

  # ═══ P2B S2r1 · 跨状态 capture 迁移一致性闸 ═══════════════════════════════
  # 先于任何 running 发射（含 starting/pre-sidecar 窗口）、pid 绑定、raw/gate 解析 fail-closed。
  # 主状态为迁移权威（M_CAPTURE_MODE 顶层已裁决：只可能是空 或 verdict_v1）。此处对资源
  # state 做【全 status】（starting/reported/resource_rejected/rejected）一致性校验：
  #   · main==verdict_v1 ⇒ 资源须显式 capture_mode==verdict_v1 且 diagnostic_output==规范 diag，
  #     否则拒绝（覆盖 resource capture 缺失 / legacy_v0 / 其它值 / diag 非规范）；
  #   · 资源声明 capture_mode 但 main 未声明 ⇒ 拒绝（含资源 verdict_v1 与任意其它非空值）；
  #   · 仅当 main 与资源都未声明 capture_mode 时才放行 legacy 路径（既有行为逐字节不变）。
  # 拒绝消息仅含 status 枚举 + 静态串，不落 raw/diag 正文/argv。
  DIAG_EXPECT="$RAW.diag.jsonl"
  R_CAPTURE_MODE=$(jq -r '.capture_mode // ""' "$R_STATE")
  if [[ "$M_CAPTURE_MODE" == "verdict_v1" ]]; then
    [[ "$R_CAPTURE_MODE" == "verdict_v1" ]] || { reject_res "capture 迁移不一致：main=verdict_v1 但 resource.capture_mode 非 verdict_v1（status=${R_STATUS}）"; exit 2; }
    [[ "$(jq -r '.diagnostic_output // ""' "$R_STATE")" == "$DIAG_EXPECT" ]] || { reject_res "capture 迁移不一致：main=verdict_v1 但 resource.diagnostic_output 非规范（status=${R_STATUS}）"; exit 2; }
  elif [[ -n "$R_CAPTURE_MODE" ]]; then
    reject_res "capture 迁移不一致：resource 声明 capture_mode 但 main 未声明（status=${R_STATUS}）"; exit 2
  fi

  # ═══ P0B3R2·C PID sidecar 绑定 ═══
  # 启动窗口（唯一 fail-open，要求 5）：仅 starting + raw_bytes==0 + 全 identity null + pid-store【缺失】→ running。
  if [[ "$R_STATUS" == "starting" && ! -e "$R_PIDS" ]]; then
    if [[ "$R_RB" -eq 0 && "$CI_PID" == "null" && "$CI_PGID" == "null" && "$CI_SID" == "null" ]]; then
      emit_running "starting/pre-sidecar"; exit 0
    fi
    reject_res "pid sidecar 缺失且非启动窗口（starting 仅在 raw_bytes==0 且 identity 全 null 时短暂放行）"; exit 2
  fi
  # 需强制 pid-store 的状态：starting（已过窗口）/reported/resource_rejected。
  # rejected（监督器 spawn 前硬错误：identity 全 null、无 pid-store）不强制 pid-store，落 switch *) fail-closed；
  #   但若其【存在】一份 pid-store，仍必须是合法对象 + 字段合法（present-but-invalid → fail-closed）。
  PIDS_REQUIRED=false
  case "$R_STATUS" in starting|reported|resource_rejected) PIDS_REQUIRED=true ;; esac
  if $PIDS_REQUIRED || [[ -e "$R_PIDS" ]]; then
    if [[ ! -e "$R_PIDS" ]]; then reject_res "pid sidecar 缺失（终态/已过启动窗口要求存在）: $R_PIDS"; exit 2; fi
    if [[ ! -f "$R_PIDS" || ! -r "$R_PIDS" ]] || ! jq -e 'type=="object"' "$R_PIDS" >/dev/null 2>&1; then
      reject_res "pid sidecar 不可读或非法 JSON 对象: $R_PIDS"; exit 2
    fi
    P_PID=$(jq -r '.pid // empty' "$R_PIDS")
    P_PGID=$(jq -r '.pgid // empty' "$R_PIDS")
    P_SID=$(jq -r '.session_id // empty' "$R_PIDS")
    P_ARGV_T=$(jq -r '.argv | type' "$R_PIDS" 2>/dev/null)
    # pid/pgid/session_id 须正整数、argv 须数组；任一缺失/非法 → fail-closed。
    if ! [[ "$P_PID" =~ ^[1-9][0-9]*$ && "$P_PGID" =~ ^[1-9][0-9]*$ && "$P_SID" =~ ^[1-9][0-9]*$ ]] || [[ "$P_ARGV_T" != "array" ]]; then
      reject_res "pid sidecar 身份字段非法（pid=$P_PID pgid=$P_PGID session_id=$P_SID argv_type=${P_ARGV_T}；须正整数 + argv 数组）"; exit 2
    fi
    # child_identity 已填充（终态）时，其 pid/pgid/session_id 必须与 pid sidecar 精确一致。
    if $CI_POPULATED; then
      if [[ "$CI_PID" != "$P_PID" || "$CI_PGID" != "$P_PGID" || "$CI_SID" != "$P_SID" ]]; then
        reject_res "resource-state child_identity 与 pid sidecar 不一致（state pid/pgid/sid=$CI_PID/$CI_PGID/$CI_SID vs sidecar=$P_PID/$P_PGID/${P_SID}）"; exit 2
      fi
    fi
  fi

  # 有界 reason / issue（用于所有终态输出/落盘，绝不 embed argv/raw/未知嵌套）。
  BREASON=$(bound512 "$R_REASON")

  # ═══ P2B S2 · verdict_v1 capture 认证 ═══════════════════════════════════
  # 仅当【资源 state 的 capture_mode == verdict_v1】才启用；缺该字段的 legacy v1 state
  # 完全不进入本块，既有行为逐字节不变。capture 认证在成功终态 reported 推进到 raw/gate
  # 解析【之前】fail-closed：任一条件不满足 → reject_res + exit 2（绝不解析 raw、绝不抽判决）。
  # resource_rejected 保持既有早拒（下方 case 已 fail-closed，不解析 raw）；starting 尚未落
  # capture 计量（zero_capture）不在此拦截。
  R_CAPTURE_MODE=$(jq -r '.capture_mode // ""' "$R_STATE")
  if [[ "$R_CAPTURE_MODE" == "verdict_v1" && "$R_STATUS" == "reported" ]]; then
    DIAG="$RAW.diag.jsonl"
    cfail() { reject_res "verdict_v1 capture 认证失败: $1"; exit 2; }
    # (1) 主状态绑定 + 资源 diagnostic_output 精确匹配规范 diag 路径。
    [[ "$(jq -r '.run.capture_mode // ""' "$STATE")"      == "verdict_v1" ]] || cfail "main.run.capture_mode!=verdict_v1"
    [[ "$(jq -r '.run.diagnostic_output // ""' "$STATE")" == "$DIAG"      ]] || cfail "main.run.diagnostic_output 非规范"
    [[ "$(jq -r '.diagnostic_output // ""' "$R_STATE")"   == "$DIAG"      ]] || cfail "resource.diagnostic_output 非规范"
    # (2) 文件系统安全：raw/diag 均不得为 symlink，存在时须普通文件；diag 须存在为可读普通文件。
    for _f in "$RAW" "$DIAG"; do
      if [[ -L "$_f" ]]; then cfail "canonical 路径为 symlink，拒绝跟随: $_f"; fi
      if [[ -e "$_f" && ! -f "$_f" ]]; then cfail "canonical 路径非普通文件: $_f"; fi
    done
    if [[ ! -f "$DIAG" || ! -r "$DIAG" ]]; then cfail "diagnostic 文件缺失/不可读: $DIAG"; fi
    if [[ ! -f "$RAW"  || ! -r "$RAW"  ]]; then cfail "raw 文件缺失/不可读: $RAW"; fi
    # (3)+(4)state 字段+(5)：类型/范围/hash/计量绑定一次 jq 校验（首个失败字段作原因）。
    CF_ERR=$(jq -r '
        def nnint: (type=="number" and .==floor and .>=0);
        # sha 字段合法性：对应 bytes>0 → 必 64 位小写 hex；否则只允许空串。
        # $b 在【根对象】上下文取值，避免管道后 . 变成字符串导致索引报错。
        def shaok($b; $s): (if $b>0 then ($s|test("^[0-9a-f]{64}$")) else $s=="" end);
        if   ((.ingress_bytes)|nnint|not) then "ingress_bytes"
        elif ((.ingress_lines)|nnint|not) then "ingress_lines"
        elif ((.verdict_bytes)|nnint|not) then "verdict_bytes"
        elif ((.verdict_lines)|nnint|not) then "verdict_lines"
        elif ((.diagnostic_bytes)|nnint|not) then "diagnostic_bytes"
        elif ((.diagnostic_lines)|nnint|not) then "diagnostic_lines"
        elif ((.preserved_count)|nnint|not) then "preserved_count"
        elif ((.denied_count)|nnint|not) then "denied_count"
        elif ((.unknown_count)|nnint|not) then "unknown_count"
        elif ((.terminal_capable_unknown_count)|nnint|not) then "terminal_capable_unknown_count"
        elif ((.diagnostic_truncated|type)!="boolean") then "diagnostic_truncated"
        elif (shaok(.ingress_bytes;    (.ingress_sha256//""))    | not) then "ingress_sha256"
        elif (shaok(.verdict_bytes;    (.verdict_sha256//""))    | not) then "verdict_sha256"
        elif (shaok(.diagnostic_bytes; (.diagnostic_sha256//"")) | not) then "diagnostic_sha256"
        elif (.raw_bytes  != .verdict_bytes)  then "raw_bytes!=verdict_bytes"
        elif (.raw_lines  != .verdict_lines)  then "raw_lines!=verdict_lines"
        elif (.raw_sha256 != .verdict_sha256) then "raw_sha256!=verdict_sha256"
        elif ((.terminal_capable_unknown_count) > 0) then "reported_terminal_unknown"
        else "" end' "$R_STATE" 2>/dev/null || echo "jq_error")
    [[ -n "$CF_ERR" ]] && cfail "字段/绑定校验($CF_ERR)"
    # (4) 磁盘实测 == 资源 state 字段（不读 raw 正文入 state，仅计量/digest）。
    V_BYTES=$(jq -r '.verdict_bytes' "$R_STATE"); V_LINES=$(jq -r '.verdict_lines' "$R_STATE"); V_SHA=$(jq -r '.verdict_sha256' "$R_STATE")
    D_BYTES=$(jq -r '.diagnostic_bytes' "$R_STATE"); D_LINES=$(jq -r '.diagnostic_lines' "$R_STATE"); D_SHA=$(jq -r '.diagnostic_sha256' "$R_STATE")
    A_RB=$(wc -c <"$RAW"  | tr -d ' '); A_RL=$(wc -l <"$RAW"  | tr -d ' ')
    A_DB=$(wc -c <"$DIAG" | tr -d ' '); A_DL=$(wc -l <"$DIAG" | tr -d ' ')
    [[ "$A_RB" == "$V_BYTES" ]] || cfail "raw on-disk bytes($A_RB)!=verdict_bytes($V_BYTES)"
    [[ "$A_RL" == "$V_LINES" ]] || cfail "raw on-disk lines($A_RL)!=verdict_lines($V_LINES)"
    [[ "$A_DB" == "$D_BYTES" ]] || cfail "diag on-disk bytes($A_DB)!=diagnostic_bytes($D_BYTES)"
    [[ "$A_DL" == "$D_LINES" ]] || cfail "diag on-disk lines($A_DL)!=diagnostic_lines($D_LINES)"
    if [[ "$V_BYTES" -gt 0 ]]; then
      [[ "$(sha256_of "$RAW")"  == "$V_SHA" ]] || cfail "raw on-disk sha256!=verdict_sha256"
    fi
    if [[ "$D_BYTES" -gt 0 ]]; then
      [[ "$(sha256_of "$DIAG")" == "$D_SHA" ]] || cfail "diag on-disk sha256!=diagnostic_sha256"
    fi
    # 认证通过 → 有界 capture 元数据（纯数值/布尔/hash + mode 标签；无 body/argv/tail/prompt/path）。
    CAPTURE_META=$(jq -c '{
        capture_mode:"verdict_v1",
        ingress_bytes, ingress_lines, ingress_sha256:(.ingress_sha256//""),
        verdict_bytes, verdict_lines, verdict_sha256:(.verdict_sha256//""),
        diagnostic_bytes, diagnostic_lines, diagnostic_sha256:(.diagnostic_sha256//""),
        diagnostic_truncated, preserved_count, denied_count, unknown_count,
        terminal_capable_unknown_count
      }' "$R_STATE" 2>/dev/null || echo "")
  fi

  case "$R_STATUS" in
    starting)
      # 启动/运行中：视作 running，只报监督器边界化 raw_bytes/raw_lines，不解析 raw、不推断判决。
      emit_running "starting"; exit 0
      ;;
    resource_rejected)
      # 已认证资源熔断终态：原子置主状态 rejected + 有界 forensic（白名单字段、无 argv/raw）。
      RES=$(res_subset "$BREASON"); [[ -n "$RES" ]] || RES=null
      BISSUE=$(bound512 "resource_rejected: $R_REASON")
      MON=$(jq -n --arg now "$(now_iso)" --arg issue "$BISSUE" --argjson res "${RES:-null}" \
            '{checked_at:$now,issues:[$issue],resource:$res}' 2>/dev/null \
            || jq -n --arg now "$(now_iso)" --arg issue "$BISSUE" '{checked_at:$now,issues:[$issue],resource:null}')
      if [[ -n "$R_EC" && "$R_EC" != "null" ]]; then
        update_state ".status=\"rejected\" | .run.exit_code=$R_EC | .monitor=$MON"
      else
        update_state ".status=\"rejected\" | .monitor=$MON"
      fi
      if ! $JSON_ONLY; then
        echo "===📡 BEGIN omp-monitor (relay verbatim)==="
        echo "🚫 omp-monitor: 资源监督器熔断 → status=rejected（fail-closed，未解析 raw、未抽判决）"
        echo "   task_id : $TASK_ID"
        echo "   reason  : $BREASON"
        echo "   forensic: raw ${R_RB}B/${R_RL}行 · sha256/tail 边界已存（未回吐 raw 正文/argv）"
        echo "   下一步   : 已 rejected。资源熔断/未确认收束绝非成功完成，不得 accept。"
        echo "===📡 END==="
      fi
      printf '{"task_id":"%s","phase":"rejected","resource_supervised":true,"reason":%s,"raw_bytes":%s,"raw_lines":%s}\n' \
        "$TASK_ID" "$(jq -Rn --arg r "$BREASON" '$r')" "$R_RB" "$R_RL"
      exit 2
      ;;
    reported)
      : # 正常完成 → 落入下方既有监控流（双层解析 + .run.exit_code sidecar 处理保持不变）。
      ;;
    *)
      # rejected（监督器自身硬错误：hard_cap_unsupported / raw_open_failed / exec_failed）：
      # 一律 fail-closed，保留（有界）监督器 reason，绝不软化成通用 parse 失败。
      RES=$(res_subset "$BREASON"); [[ -n "$RES" ]] || RES=null
      BISSUE=$(bound512 "resource-supervisor $R_STATUS: $R_REASON")
      MON=$(jq -n --arg now "$(now_iso)" --arg issue "$BISSUE" --argjson res "${RES:-null}" \
            '{checked_at:$now,issues:[$issue],resource:$res}' 2>/dev/null \
            || jq -n --arg now "$(now_iso)" --arg issue "$BISSUE" '{checked_at:$now,issues:[$issue],resource:null}')
      if [[ -n "$R_EC" && "$R_EC" != "null" ]]; then
        update_state ".status=\"rejected\" | .run.exit_code=$R_EC | .monitor=$MON"
      else
        update_state ".status=\"rejected\" | .monitor=$MON"
      fi
      echo "🚫 omp-monitor: 资源监督器终态=${R_STATUS}（${BREASON}）→ status=rejected（fail-closed）" >&2
      printf '{"task_id":"%s","phase":"rejected","resource_supervised":true,"reason":%s}\n' "$TASK_ID" "$(jq -Rn --arg r "$BREASON" '$r')"
      exit 2
      ;;
  esac
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

# Shell async 由后台 wrapper 把真实退出码写到 sidecar；进程已结束但 sidecar 缺失也必须失败关闭。
if [[ "$RUN_MODE" == "async" && -z "$EC" ]]; then
  if [[ -s "$RAW.exit" ]]; then
    EC=$(tr -d '[:space:]' < "$RAW.exit")
    [[ "$EC" =~ ^[0-9]+$ ]] || EC=125
    update_state ".run.exit_code=$EC"
  else
    update_state ".status=\"rejected\" | .run.exit_code=125 | .monitor={checked_at:\"$(now_iso)\",issues:[\"async 退出码 sidecar 缺失\"]}"
    echo "🚫 omp-monitor: async 进程已结束但退出码未知 → status=rejected" >&2
    exit 2
  fi
fi

# ── 完成：raw 须存在非空 ──
if [[ ! -s "$RAW" ]]; then
  update_state ".status=\"rejected\" | .monitor={checked_at:\"$(now_iso)\",issues:[\"raw 缺失或空\"]}"
  echo "🚫 omp-monitor: raw 缺失/空 → status=rejected" >&2
  exit 2
fi

ISSUES=(); REJECT=false; EXITCODE=0
# ── Package C：紧凑诊断（拒绝且非 execute 时落 .monitor.compact_debug，绝不回吐 raw）──
FAILSTAGE=""; GATE_REASON=""; CDBG="null"; CDBG_PRESENT=false

# ── 传输层①：turn_end 完整性校验（全部模式）──
if ! jsonl_has_turn_end "$RAW"; then
  ISSUES+=("JSONL 缺 turn_end"); REJECT=true; EXITCODE=2; [[ -z "$FAILSTAGE" ]] && FAILSTAGE="turn_end"
fi

# ── 传输层 + 应用层①②③：gate-verify（execute 模式跳过）──
if [[ "$MONITOR_MODE" != "execute" ]]; then
  set +e
  GV_OUT=$(bash "$GATE/gate-verify.sh" --mode output --file "$RAW" 2>/dev/null); GV_RC=$?
  set -e
  if [[ $GV_RC -eq 10 ]]; then
    ISSUES+=("evidence 为空（gate-verify exit 10）"); REJECT=true; EXITCODE=10
    [[ -z "$FAILSTAGE" ]] && FAILSTAGE="evidence_empty"
    GATE_REASON="evidence 为空"
  elif [[ $GV_RC -ne 0 ]]; then
    GATE_REASON=$(echo "$GV_OUT" | jq -r '.reason' 2>/dev/null || echo "$GV_OUT")
    ISSUES+=("输出结构不合格: $GATE_REASON"); REJECT=true; EXITCODE=1
    [[ -z "$FAILSTAGE" ]] && FAILSTAGE="gate_verify"
  fi
fi

# ── 提取内层审计 JSON（execute 模式跳过校验）──
if [[ "$MONITOR_MODE" != "execute" ]]; then
# ── 提取内层审计 JSON（用于 severity/summary 校验 + 存档供 finish）──
# 稳健提取：取"最后一个合法判决对象"（跳过前置陈旧/非法草稿）；无合法判决时退化取
# 最后一个 JSON 对象，让下方 severity/summary 校验能给出精确错误而非笼统"无 JSON"。
FINAL=$(jsonl_final_text "$RAW")
INNER=$(extract_verdict_json "$FINAL" 2>/dev/null || true)
[[ -z "$INNER" ]] && INNER=$(extract_last_json_object "$FINAL" 2>/dev/null || true)
[[ -z "$INNER" ]] && INNER=$(extract_inner_json "$FINAL" 2>/dev/null || true)
# 可选紧凑调试摘要（OMP_DEBUG=1 时）：只出 bytes/lines/候选数/final_text 尾部，绝不回吐整个 raw。
if [[ -n "${OMP_DEBUG:-}" ]]; then
  _dbg_sz=$(wc -c <"$RAW" 2>/dev/null | tr -d ' '); _dbg_ln=$(wc -l <"$RAW" 2>/dev/null | tr -d ' ')
  _dbg_nc=$(printf '%s' "$FINAL" | _json_objects_nul | tr -cd '\0' | wc -c | tr -d ' ')
  echo "🔎 omp-monitor debug · raw=${_dbg_sz}B/${_dbg_ln}行 · 候选对象=${_dbg_nc} · final_text 尾部:" >&2
  printf '%s' "${FINAL: -2000}" >&2; echo >&2
fi
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
  [[ -z "$FAILSTAGE" ]] && FAILSTAGE=$([[ -z "$INNER" ]] && echo "no_verdict_json" || echo "severity")
fi
# 应用层⑤：summary 非空
if [[ "$REJECT" == false && -z "$SUMMARY" ]]; then
  ISSUES+=("缺 summary 结论摘要"); REJECT=true; EXITCODE=1
  [[ -z "$FAILSTAGE" ]] && FAILSTAGE="summary"
fi

fi  # end of execute skip
# ── stopReason / 退出码（同步有 EC；async 用 turn_end 兜底）──
STOP=$(jsonl_stop_reason "$RAW"); [[ -z "$STOP" ]] && STOP="unknown"
if [[ "$STOP" != "stop" ]]; then
  ISSUES+=("OMP 未正常收尾：stopReason=${STOP}（须 stop）"); REJECT=true; EXITCODE=2
  [[ -z "$FAILSTAGE" ]] && FAILSTAGE="stop_reason"
fi
if [[ -n "$EC" && "$EC" != "null" && "$EC" -ne 0 ]]; then
  ISSUES+=("omp 退出码非 0（${EC}）"); REJECT=true; [[ $EXITCODE -eq 0 ]] && EXITCODE=2
  [[ -z "$FAILSTAGE" ]] && FAILSTAGE="exit_code"
fi

# ── Package C：拒绝且非 execute → 构建紧凑诊断（capped，绝不回吐 raw）──
# 只出 bytes/lines/候选数/keys/尾部片段，供事后诊断拒绝原因而无需把上百 KB raw 打进上下文。
build_compact_debug() {
  local errf="$RAW.err" has_err=false errtail=""
  local rb rl fb nc keys parse ftail stage
  rb=$(wc -c <"$RAW" 2>/dev/null | tr -d ' '); [[ "$rb" =~ ^[0-9]+$ ]] || rb=0
  rl=$(wc -l <"$RAW" 2>/dev/null | tr -d ' '); [[ "$rl" =~ ^[0-9]+$ ]] || rl=0
  fb=$(printf '%s' "${FINAL:-}" | wc -c | tr -d ' '); [[ "$fb" =~ ^[0-9]+$ ]] || fb=0
  nc=$(printf '%s' "${FINAL:-}" | _json_objects_nul | tr -cd '\0' | wc -c | tr -d ' '); [[ "$nc" =~ ^[0-9]+$ ]] || nc=0
  if [[ -n "${INNER:-}" ]] && inner_json_valid "${INNER:-}"; then
    parse=true; keys=$(printf '%s' "$INNER" | jq -c 'keys' 2>/dev/null || echo '[]')
  else parse=false; keys='[]'; fi
  [[ "$keys" =~ ^\[ ]] || keys='[]'
  ftail="${FINAL: -800}"
  if [[ -f "$errf" ]]; then has_err=true; errtail=$(tail -c 800 "$errf" 2>/dev/null || true); fi
  # 比 gate_verify 更细：先按最终 assistant 文本/JSON 候选诊断，再保留 gate_reason 作为原始 gate 结果。
  stage="${FAILSTAGE:-unknown}"
  if [[ $fb -eq 0 ]]; then stage="no_final_text"
  elif [[ $nc -eq 0 ]]; then stage="no_candidate"
  elif [[ -z "${INNER:-}" ]]; then stage="no_verdict_json"
  elif [[ "$parse" != true && "$stage" == "gate_verify" ]]; then stage="invalid_inner"
  fi
  jq -n \
    --arg raw "$RAW" --arg errf "$errf" --argjson has_err "$has_err" \
    --argjson rb "$rb" --argjson rl "$rl" --arg errtail "$errtail" \
    --arg stop "${STOP:-unknown}" --arg greason "${GATE_REASON:-}" \
    --argjson fb "$fb" --argjson nc "$nc" --argjson parse "$parse" \
    --argjson keys "$keys" --arg stage "$stage" --arg ftail "$ftail" \
    '{raw_output:$raw, raw_err:(if $has_err then $errf else null end),
      raw_bytes:$rb, raw_lines:$rl,
      raw_err_tail:(if $has_err then $errtail else null end),
      stop_reason:$stop, gate_reason:$greason,
      final_text_bytes:$fb, candidate_count:$nc,
      last_candidate_parseable:$parse, last_candidate_keys:$keys,
      failure_stage:$stage, final_text_tail:$ftail}' 2>/dev/null || echo null
}
if [[ "$MONITOR_MODE" != "execute" && "$REJECT" == true ]]; then
  CDBG=$(build_compact_debug); [[ -n "$CDBG" ]] || CDBG="null"
  [[ "$CDBG" != "null" ]] && CDBG_PRESENT=true
fi

# ── execute 模式：设置默认值后再写 MON ──
if [[ "$MONITOR_MODE" == "execute" ]]; then
  SEV="completed"
  SEV_VALID=true
  # 先完整提取，再由 Bash 截取摘要。禁止 `producer | head`：在 pipefail 下长文本会
  # 让 producer 收到 SIGPIPE，monitor 以 141 退出并把 state 永久留在 running。
  FINAL=$(jsonl_final_text "$RAW")
  SUMMARY="${FINAL:0:160}"
  EVN=0
  INNER="{}"
fi

# ── P1B：required_actions 双写（加性、向后兼容）──
# P1A gate（gate-verify --mode output）已在上方成功路径前校验过任何“出现”的 required_actions 字段，
# 故此处只做原样持久化，不再重复校验、不发明修复动作、不因缺字段而拒绝：
#   · 内层 JSON 提供 required_actions 数组 → 原样落 .monitor.required_actions（保序、逐字节）。
#   · legacy 判决缺该字段（含 execute 的非适用形态 INNER={}）→ required_actions=null + required_actions_legacy=true。
RA_JSON="null"; RA_LEGACY=true
if [[ -n "${INNER:-}" && "${INNER}" != "null" ]] && inner_json_valid "${INNER:-}"; then
  if printf '%s' "$INNER" | jq -e '(.required_actions|type)=="array"' >/dev/null 2>&1; then
    RA_JSON=$(printf '%s' "$INNER" | jq -c '.required_actions'); RA_LEGACY=false
  fi
fi

# ── 写监控报告到 state ──
# 空数组直接 []（不能走 grep 管道：空时 grep exit 1 触发 pipefail，|| echo 会追加成 "[]\n[]"）
if [[ ${#ISSUES[@]} -eq 0 ]]; then ISSUES_J='[]'
else ISSUES_J=$(printf '%s\n' "${ISSUES[@]}" | jq -R . | jq -sc .); fi
MON=$(jq -n --arg now "$(now_iso)" --arg sev "$SEV" --arg sum "$SUMMARY" \
   --argjson evn "${EVN:-0}" --arg stop "$STOP" --argjson sv "$SEV_VALID" \
   --argjson issues "$ISSUES_J" --argjson inner "${INNER:-null}" --argjson cdbg "${CDBG:-null}" \
   --argjson ra "${RA_JSON:-null}" --argjson ralegacy "$RA_LEGACY" \
   '{checked_at:$now,severity:$sev,severity_valid:$sv,summary:$sum,evidence_count:$evn,stop_reason:$stop,issues:$issues,inner:$inner,required_actions:$ra,required_actions_legacy:$ralegacy,compact_debug:$cdbg}' 2>/dev/null \
   || jq -n --arg now "$(now_iso)" --argjson issues "$ISSUES_J" --argjson cdbg "${CDBG:-null}" '{checked_at:$now,issues:$issues,inner:null,required_actions:null,required_actions_legacy:true,compact_debug:$cdbg}')

if $REJECT; then
  update_state ".status=\"rejected\" | .monitor=$MON"
  NEWSTATUS="rejected"
else
  update_state ".status=\"reported\" | .monitor=$MON"
  NEWSTATUS="reported"
fi
# P2B S2：已认证 verdict_v1 capture → 附加有界 capture 元数据到 .monitor（数值/布尔/hash 子集，
# 无 raw 正文/argv/tail/prompt）。仅 authenticated reported 路径非空；legacy/非监督恒空 → 无副作用。
if [[ -n "$CAPTURE_META" ]]; then
  update_state ".monitor.capture=$CAPTURE_META"
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
    $CDBG_PRESENT && echo "   🔎 诊断   : 紧凑诊断已落 .monitor.compact_debug（failure_stage=${FAILSTAGE:-unknown}，含 final_text 尾部/候选数，未回吐原始 raw）"
  fi
  echo "===📡 END==="
fi
printf '{"task_id":"%s","phase":"%s","severity":"%s","severity_valid":%s,"evidence_count":%s,"stop_reason":"%s","issues":%s,"compact_debug":%s}\n' \
  "$TASK_ID" "$NEWSTATUS" "$SEV" "$SEV_VALID" "${EVN:-0}" "$STOP" "$ISSUES_J" "$CDBG_PRESENT"
exit $EXITCODE
