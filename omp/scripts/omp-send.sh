#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-send.sh —— 四步②：渲染 OMP prompt 并按通道调用 omp
#
# 通道优先级（最新设计）：RPC（过渡首选）> Shell（快速单次降级）> ACP（终局·预留）。
#   RPC   : omp --mode rpc 持续连接（NDJSON stdio）；daemon 常驻、fifo 发 prompt、stdout 落盘。
#           天然异步——发 prompt 立即返回，omp-monitor 轮询 turn_end + daemon 心跳。
#   Shell : omp -p --mode json 单次进程（同步/--async）。RPC 启动/就绪失败时自动降级到此。
#   ACP   : delegate_task(acp_command='omp') 终局路径。omp-send 渲染 prompt、写 state、\n#           output 指导 Hermes 调用 delegate_task；实现见 §3。
#
# 真实接口（v16.2.2 实测）：
#   RPC  : omp --mode rpc --append-system-prompt <模板> --no-session --tools <白名单> [--cwd][--advisor]
#          stdin: {"type":"prompt","message":"<任务正文>"}  → stdout: 每 turn JSONL（…turn_end）
#   Shell: omp -p --mode json --no-session --max-time N --tools <白名单> [--cwd][--advisor]
#          --append-system-prompt <模板> "<任务正文>"
#   两通道输出同构 JSONL，由 omp-monitor.sh 双层解析（传输层 jq + 应用层内层 JSON）。
#
# 安全默认：只读工具白名单 read,grep,glob,lsp,web_search；放开写需 --allow-write。
#
# 参数：
#   --state <file>     omp-start.sh 写的状态文件（必填）
#   --channel rpc|shell  覆盖委派包通道（默认用委派包 .channel；start 默认 rpc）
#   --max-time <N>     超时秒数（shell=omp --max-time；rpc=holder 存活上限）（默认 300）
#   --async            Shell 通道后台跑（rpc 本就异步，此 flag 对 rpc 无意义）
#   --advisor          附加 omp --advisor（实测 print/rpc 下不注入额外结构，语义见 references）
#   --allow-write      放开写工具白名单（危险；仅 govern:clean/deep-clean/sql + rollback 时）
#   --no-auto-approve  关闭 --auto-approve（默认开；只读白名单下安全）
#   --no-fallback      RPC 失败时不降级 Shell（直接报错，便于诊断）
#   --dry-run          只渲染 prompt + 打印将执行的命令，不真调用
#   -h|--help
#
# 退出码： 0 已发起（status=running；dry-run 也 0）· 2 状态非 gated/读不到
#          · 3 通道不可用（rpc 失败 w/o fallback / omp 缺失且无降级）· 20 轮次超限（拒发）
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SELF_DIR/lib/omp-lib.sh"
GATE="$SELF_DIR/gate"; TPL_DIR="$SELF_DIR/../templates"

STATE=""; CH_OVERRIDE=""; MAXTIME=300; ASYNC=false; ADVISOR=false; ALLOW_WRITE=false
AUTO_APPROVE=true; DRY=false; FALLBACK=true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state)           STATE="$2"; shift 2 ;;
    --channel)         CH_OVERRIDE="$2"; shift 2 ;;
    --max-time)        MAXTIME="$2"; shift 2 ;;
    --async)           ASYNC=true; shift ;;
    --advisor)         ADVISOR=true; shift ;;
    --allow-write)     ALLOW_WRITE=true; shift ;;
    --no-auto-approve) AUTO_APPROVE=false; shift ;;
    --no-fallback)     FALLBACK=false; shift ;;
    --dry-run)         DRY=true; shift ;;
    -h|--help)         sed -n '2,44p' "$0"; exit 0 ;;
    *) echo "omp-send: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ -n "$STATE" && -r "$STATE" ]] || { echo "omp-send: 读不到 --state '$STATE'" >&2; exit 2; }

PKG=$(jq -c '.package' "$STATE")
TASK_ID=$(jq -r '.task_id' "$STATE")
STATUS=$(jq -r '.status' "$STATE")
CHANNEL=$(jq -r '.channel // "acp"' "$STATE")
[[ -n "$CH_OVERRIDE" ]] && CHANNEL="$CH_OVERRIDE"
[[ "$STATUS" == "gated" ]] || { echo "omp-send: status=${STATUS}（需 gated 才能发送；先过 omp-start）" >&2; exit 2; }

update_state() { local f="$1"; local s; s=$(jq "$f | .updated_at=\"$(now_iso)\"" "$STATE"); printf '%s' "$s" | atomic_write "$STATE"; }

# ── gate-counter：本次 send = 一轮 ──
set +e
C_OUT=$(bash "$GATE/gate-counter.sh" --task-id "$TASK_ID" --inc-round \
        --round-limit "$(echo "$PKG" | jq -r '.threshold.round_limit')" \
        --reject-limit "$(echo "$PKG" | jq -r '.threshold.reject_limit')" 2>/dev/null); C_RC=$?
set -e
if [[ $C_RC -eq 20 ]]; then
  echo "⛔ omp-send: 轮次超限，硬终止（不发送）: $C_OUT" >&2
  echo "   → 停循环，升级人工复核或转 cc-tmux。" >&2
  exit 20
fi
ROUND=$(echo "$C_OUT" | jq -r '.round_count')

# ── 渲染 prompt（两通道共用 SYS + USER_MSG）──
MODE_FULL=$(echo "$PKG" | jq -r '.mode')
BASE_MODE="${MODE_FULL%%:*}"; SUBMODE="${MODE_FULL#*:}"; [[ "$SUBMODE" == "$MODE_FULL" ]] && SUBMODE=""
TASK=$(echo "$PKG" | jq -r '.task')
CWD=$(echo "$PKG" | jq -r '.scope.cwd // ""')
ALLOWED=$(echo "$PKG" | jq -rc '.scope.allowed_paths // []')
DENIED=$(echo "$PKG" | jq -rc '.scope.denied_paths // []')
CRIT_LIST=$(echo "$PKG" | jq -r '.criterion[] | "  - " + .')
RL=$(echo "$PKG" | jq -r '.threshold.round_limit')
JL=$(echo "$PKG" | jq -r '.threshold.reject_limit')

if [[ "$BASE_MODE" == "govern" ]]; then TPL="$TPL_DIR/govern-prompt-template.md"; else TPL="$TPL_DIR/audit-prompt-template.md"; fi
if [[ -r "$TPL" ]]; then SYS=$(cat "$TPL"); else
  SYS="你是独立审查者。只输出一个 JSON 对象（可包在 \`\`\`json 围栏里），字段：severity(nit|concern|blocker|pass)、summary、evidence(数组，每项 {type,ref} 指真实文件/命令/行号；不得为空)、reject_instruction。不采信无证据的结论。"
fi

USER_MSG=$(cat <<EOF
[OMP 委派任务 · task_id=$TASK_ID · mode=$MODE_FULL · 第 $ROUND 轮]

任务：
$TASK

scope（严格遵守，越界即视为失败）：
  允许路径：$ALLOWED
  禁止路径：$DENIED
  工作目录：${CWD:-（未指定，默认当前）}
$( [[ -n "$SUBMODE" ]] && echo "治理子模式：$SUBMODE" )

可裁决验收条件（逐条核对）：
$CRIT_LIST

约束：
  - 严格按 system 提示的 JSON schema 输出（severity / summary / evidence / reject_instruction）。
  - evidence 必须是真实的文件路径+行号 / 命令+输出 / 测试结果，禁止空数组、禁止只写自然语言总结。
  - 本任务轮次上限 ${RL}、reject 上限 ${JL}；不要绕过 scope。
EOF
)

# ── 工具白名单 ──
TOOLS="read,grep,glob,lsp,web_search"
if $ALLOW_WRITE; then TOOLS="read,grep,glob,lsp,web_search,write,edit,bash"; fi

RAW="$(raw_path "$TASK_ID")"; PROMPT="$(prompt_path "$TASK_ID")"
printf '%s\n' "$USER_MSG" | atomic_write "$PROMPT"

# ── dry-run：只渲染不发 ──
if $DRY; then
  echo "===📋 BEGIN omp-send --dry-run (relay verbatim)==="
  echo "channel=$CHANNEL  task_id=$TASK_ID  mode=$MODE_FULL  round=$ROUND  tools=$TOOLS  max-time=$MAXTIME"
  if [[ "$CHANNEL" == "rpc" ]]; then
    echo "rpc daemon: $OMP_BIN --mode rpc --no-session --tools $TOOLS ${CWD:+--cwd $CWD} ${AUTO_APPROVE:+--auto-approve}${ADVISOR:+ --advisor} --append-system-prompt <sys>"
    echo "rpc stdin : $(jq -cn --arg m "$USER_MSG" '{type:"prompt",message:$m}' | head -c 160)…"
  else
    echo "shell cmd : $OMP_BIN -p --mode json --no-session --max-time $MAXTIME --tools $TOOLS ${CWD:+--cwd $CWD} … --append-system-prompt <sys> <user_msg>"
  fi
  echo "--- 渲染的任务正文（${PROMPT}）---"; printf '%s\n' "$USER_MSG"
  echo "===📋 END（dry-run 未调用 omp）==="
  exit 0
fi

# ════ Shell 通道（也是 RPC 的降级目标）════════════════════════════
shell_send() {
  if ! omp_available; then
    update_state ".status=\"rejected\" | .gate.reason=\"channel_error: omp CLI 不存在\""
    echo "🚫 omp-send: omp 不可用 → status=rejected (channel_error)" >&2; return 3
  fi
  local args=(-p --mode json --no-session --max-time "$MAXTIME" --tools "$TOOLS")
  $AUTO_APPROVE && args+=(--auto-approve)
  [[ -n "$CWD" ]] && args+=(--cwd "$CWD")
  $ADVISOR && args+=(--advisor)
  args+=(--append-system-prompt "$SYS" "$USER_MSG")
  update_state ".status=\"running\" | .run.channel_used=\"shell\" | .run.raw_output=\"$RAW\" | .run.started_at=\"$(now_iso)\" | .run.round=$ROUND"
  if $ASYNC; then
    if command -v perl >/dev/null 2>&1; then
      ( perl -e 'alarm shift; exec @ARGV or exit 127' "$((MAXTIME + 30))" "$OMP_BIN" "${args[@]}" >"$RAW" 2>"$RAW.err" </dev/null ) &
    else ( "$OMP_BIN" "${args[@]}" >"$RAW" 2>"$RAW.err" </dev/null ) & fi
    local pid=$!; disown 2>/dev/null || true
    update_state ".run.pid=$pid | .run.mode=\"async\""
    echo "===📋 BEGIN omp-send shell --async (relay verbatim)==="
    echo "🚀 已后台发起 omp（第 $ROUND 轮）· pid=$pid · raw=$RAW"
    echo "   监控: omp-monitor.sh --state $STATE   · 干预: kill $pid"
    echo "===📋 END==="; return 0
  fi
  set +e; run_omp_timed "$MAXTIME" "${args[@]}" >"$RAW" 2>"$RAW.err"; local ec=$?; set -e
  update_state ".run.exit_code=$ec | .run.mode=\"sync\""
  if [[ $ec -ne 0 && ! -s "$RAW" ]]; then
    update_state ".status=\"rejected\" | .gate.reason=\"channel_error: omp 退出码 $ec 且无输出\""
    echo "🚫 omp-send: omp 退出码 $ec 且无输出 → status=rejected" >&2; return 3
  fi
  echo "===📋 BEGIN omp-send shell (relay verbatim)==="
  echo "✅ omp 同步执行完毕（第 $ROUND 轮）exit=$ec · raw=$RAW ($(wc -c <"$RAW" | tr -d ' ')B)"
  echo "   下一步: omp-monitor.sh --state $STATE"
  echo "===📋 END==="; return 0
}

# ════ RPC 通道（omp --mode rpc 持续连接）════════════════════════════
rpc_send() {
  omp_available || { warn "rpc: omp 不存在"; return 1; }
  local fifo dpid hpid tsl
  fifo="$(fifo_path "$TASK_ID")"
  dpid=$(jq -r '.run.rpc_pid // empty' "$STATE")
  hpid=$(jq -r '.run.holder_pid // empty' "$STATE")
  # 复用存活 daemon；否则新建
  if ! rpc_daemon_alive "$dpid"; then
    rpc_stop "$TASK_ID" "$dpid" "$hpid"   # 清旧残留
    rm -f "$fifo"; mkfifo "$fifo" 2>/dev/null || { warn "rpc: mkfifo 失败"; return 1; }
    : > "$RAW"; : > "$RAW.err"
    # holder 保持 fifo 写端（sleep MAXTIME），否则 daemon 读 EOF 自退。
    # 关键：</dev/null + 2>/dev/null 切断对父进程 stdin/stderr 的继承——否则当 send 被
    # `2>&1 | grep` 之类管道调用时，holder 继承管道写端 fd，会让上游管道 MAXTIME 不结束。
    ( sleep "$MAXTIME" > "$fifo" 2>/dev/null ) </dev/null & hpid=$!
    local dargs=(--mode rpc --no-session --tools "$TOOLS")
    $AUTO_APPROVE && dargs+=(--auto-approve)
    [[ -n "$CWD" ]] && dargs+=(--cwd "$CWD")
    $ADVISOR && dargs+=(--advisor)
    dargs+=(--append-system-prompt "$SYS")
    ( "$OMP_BIN" "${dargs[@]}" < "$fifo" > "$RAW" 2> "$RAW.err" ) & dpid=$!
    disown 2>/dev/null || true
    # 等 ready；daemon 早死立即降级（不空等满 15s）
    local k=0 ready=0
    while [[ $k -lt 60 ]]; do
      if [[ -f "$RAW" ]] && grep -q '"type":"ready"' "$RAW" 2>/dev/null; then ready=1; break; fi
      rpc_daemon_alive "$dpid" || break
      sleep 0.25; k=$((k + 1))
    done
    if [[ $ready -ne 1 ]]; then
      warn "rpc: daemon 未就绪（超时或早退）"; rpc_stop "$TASK_ID" "$dpid" "$hpid"; return 1
    fi
    update_state ".run.rpc_pid=$dpid | .run.holder_pid=$hpid | .run.fifo=\"$fifo\""
  fi
  # 发 prompt（记 turn 起始行 marker，供 monitor 只看本轮）
  tsl=$(wc -l < "$RAW" | tr -d ' ')
  jq -cn --arg m "$USER_MSG" '{type:"prompt",message:$m}' > "$fifo" || { warn "rpc: 写 fifo 失败"; return 1; }
  update_state ".status=\"running\" | .run.channel_used=\"rpc\" | .run.mode=\"rpc\" | .run.raw_output=\"$RAW\" | .run.rpc_pid=$dpid | .run.holder_pid=$hpid | .run.fifo=\"$fifo\" | .run.turn_start_line=$tsl | .run.started_at=\"$(now_iso)\" | .run.round=$ROUND"
  echo "===📋 BEGIN omp-send rpc (relay verbatim)==="
  echo "🚀 RPC 已发 prompt（第 $ROUND 轮，持续连接）"
  echo "   task_id : $TASK_ID   daemon pid: $dpid   raw: $RAW"
  echo "   监控    : omp-monitor.sh --state $STATE   （轮询 turn_end + daemon 心跳）"
  echo "   干预    : kill $dpid   （随时中断）"
  echo "===📋 END==="; return 0
}

# ── 通道分派 ──
case "$CHANNEL" in
  acp)
    # ACP: spawn OMP as sub-agent via delegate_task(acp_command='omp').
    # omp acp starts ACP server over stdio; prompt delivered via ACP protocol.
    # This script prepares state; Hermes reads it and calls delegate_task.
    update_state ".status=\"pending_acp\" | .run.channel_used=\"acp\" | .run.mode=\"acp\" | .run.prompt=\"$PROMPT\" | .run.raw_output=\"$RAW\" | .run.task=\"$TASK\" | .run.started_at=\"$(now_iso)\" | .run.round=$ROUND"
    echo "===📋 BEGIN omp-send acp (relay verbatim)==="
    echo "🔷 ACP 委托 · task_id=$TASK_ID · round=$ROUND"
    echo "   prompt : $PROMPT"
    echo "   raw    : $RAW"
    echo "   下一步: Hermes 调用 delegate_task(acp_command='omp', goal=<PROMPT内容>)"
    echo "===📋 END==="; exit 0 ;;
  rpc)
    set +e; rpc_send; rc=$?; set -e
    if [[ $rc -eq 0 ]]; then exit 0; fi
    if $FALLBACK; then
      warn "RPC 不可用 → 降级 Shell（快速单次）"
      update_state ".run.degraded_from=\"rpc\""
      set +e; shell_send; rc=$?; set -e; exit $rc
    else
      update_state ".status=\"rejected\" | .gate.reason=\"rpc_unavailable 且 --no-fallback\""
      echo "🚫 omp-send: RPC 不可用且 --no-fallback → status=rejected" >&2; exit 3
    fi ;;
  shell)
    set +e; shell_send; rc=$?; set -e; exit $rc ;;
  *)
    echo "omp-send: 未知通道 '$CHANNEL'（须 rpc|shell|acp）" >&2; exit 3 ;;
esac
