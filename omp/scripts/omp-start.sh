#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-start.sh —— 四步①：生成委派包 + 跑 gate + 写状态权威文件
#
# 职责：把 Hermes 的审计/治理意图固化为委派包 JSON，过 gate-verify（字段完整）+
#       gate-danger（危险/scope/rollback/凭据），并写出状态权威文件。不调用 omp。
#
# 输入（二选一）：
#   --package-json <file|->   完整委派包 JSON（推荐：Hermes 用 jq 构造；- 表示 stdin）
#   或便捷参数自行拼装：
#     --task <文本>           任务说明（必填）
#     --mode <m>             audit|govern:inspect|govern:clean|govern:deep-clean|govern:evidence|govern:sql（默认 audit）
#     --channel <c>          rpc|shell|acp（默认 rpc 过渡首选；rpc 失败自动降级 shell；acp 终局预留）
#     --cwd <dir>            scope 工作目录（危险任务必填其一：cwd 或 allowed-path）
#     --allowed-path <p>     允许路径（可重复）
#     --denied-path <p>      禁止路径（可重复）
#     --criterion <c>        可裁决验收条件（可重复，至少一条）
#     --round-limit <N>      默认 3
#     --reject-limit <N>     默认 2
#     --risk-level <l>       low|medium|high（默认 low）
#     --dangerous-mode <m>   声明的危险模式（可重复，如 clean/sql）
#     --rollback <文本>      回滚说明（clean/deep-clean/sql 必填）
#   公共：
#     --task-id <id>         指定 task_id（默认自动 omp-YYYYMMDD-HHMMSS）
#     -h|--help
#
# 退出码： 0 gate 全过（status=gated）· 2 gate 失败（status=created+gate_failed）
#          · 3 omp 不可用（channel_unavailable）/ 参数错误
# stdout： task_id 与状态文件路径（供 omp-send.sh 消费）+ 委派包摘要
# 状态文件：${OMP_TMPDIR:-/tmp}/omp-state-<task_id>.json
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SELF_DIR/lib/omp-lib.sh"
GATE="$SELF_DIR/gate"

PKG_JSON_SRC=""; TASK=""; MODE="audit"; CHANNEL="rpc"; CWD=""; ROLLBACK=""
RISK_LEVEL="low"; ROUND_LIMIT=3; REJECT_LIMIT=2; TASK_ID=""
ALLOWED=(); DENIED=(); CRIT=(); DMODES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --package-json) PKG_JSON_SRC="$2"; shift 2 ;;
    --task)         TASK="$2"; shift 2 ;;
    --mode)         MODE="$2"; shift 2 ;;
    --channel)      CHANNEL="$2"; shift 2 ;;
    --cwd)          CWD="$2"; shift 2 ;;
    --allowed-path) ALLOWED+=("$2"); shift 2 ;;
    --denied-path)  DENIED+=("$2"); shift 2 ;;
    --criterion)    CRIT+=("$2"); shift 2 ;;
    --round-limit)  ROUND_LIMIT="$2"; shift 2 ;;
    --reject-limit) REJECT_LIMIT="$2"; shift 2 ;;
    --risk-level)   RISK_LEVEL="$2"; shift 2 ;;
    --dangerous-mode) DMODES+=("$2"); shift 2 ;;
    --rollback)     ROLLBACK="$2"; shift 2 ;;
    --task-id)      TASK_ID="$2"; shift 2 ;;
    -h|--help)      sed -n '2,43p' "$0"; exit 0 ;;
    *) echo "omp-start: 未知参数 $1" >&2; exit 3 ;;
  esac
done

arr_json() { local a=() x; for x in "$@"; do [[ -n "$x" ]] && a+=("$x"); done
  [[ ${#a[@]} -eq 0 ]] && { echo "[]"; return; }; printf '%s\n' "${a[@]}" | jq -R . | jq -sc .; }

# ── 构造委派包 ─────────────────────────────────────────────────────
if [[ -n "$PKG_JSON_SRC" ]]; then
  if [[ "$PKG_JSON_SRC" == "-" ]]; then PKG=$(cat); else PKG=$(cat "$PKG_JSON_SRC"); fi
  echo "$PKG" | jq -e 'type=="object"' >/dev/null 2>&1 || { echo "omp-start: --package-json 非合法 JSON 对象" >&2; exit 3; }
  # 补 task_id（若缺）
  [[ -z "$TASK_ID" ]] && TASK_ID=$(echo "$PKG" | jq -r '.task_id // empty')
  [[ -z "$TASK_ID" ]] && TASK_ID="omp-$(date +%Y%m%d-%H%M%S)"
  PKG=$(echo "$PKG" | jq --arg id "$TASK_ID" '.task_id=$id')
else
  [[ -n "$TASK" ]]        || { echo "omp-start: 缺 --task（或用 --package-json）" >&2; exit 3; }
  [[ ${#CRIT[@]} -gt 0 ]] || { echo "omp-start: 至少一条 --criterion" >&2; exit 3; }
  [[ -z "$TASK_ID" ]] && TASK_ID="omp-$(date +%Y%m%d-%H%M%S)"
  ALLOWED_J=$(arr_json "${ALLOWED[@]:-}"); DENIED_J=$(arr_json "${DENIED[@]:-}")
  CRIT_J=$(arr_json "${CRIT[@]:-}");       DMODES_J=$(arr_json "${DMODES[@]:-}")
  PKG=$(jq -n \
    --arg id "$TASK_ID" --arg ch "$CHANNEL" --arg mode "$MODE" --arg task "$TASK" \
    --arg cwd "$CWD" --arg rb "$ROLLBACK" --arg rl "$RISK_LEVEL" \
    --argjson allowed "$ALLOWED_J" --argjson denied "$DENIED_J" \
    --argjson crit "$CRIT_J" --argjson dmodes "$DMODES_J" \
    --argjson roundl "$ROUND_LIMIT" --argjson rejl "$REJECT_LIMIT" \
    '{task_id:$id,channel:$ch,mode:$mode,task:$task,
      scope:{allowed_paths:$allowed,denied_paths:$denied,cwd:$cwd},
      criterion:$crit,
      threshold:{round_limit:$roundl,reject_limit:$rejl},
      risk:({level:$rl,dangerous_modes:$dmodes} + (if $rb!="" then {rollback:$rb} else {} end)),
      auditor:{required:true,independence_level:"independent_readonly"},
      output:{format:"json",evidence_required:true}}')
fi

CHANNEL=$(echo "$PKG" | jq -r '.channel // "rpc"')
PKG_TMP="$OMP_TMPDIR/omp-pkg-${TASK_ID}.json"
echo "$PKG" | atomic_write "$PKG_TMP"
STATE="$(state_path "$TASK_ID")"

# write_state <status> <gate_failed_bool> <reason> <verify_json> <danger_json>
write_state() {
  jq -n --argjson pkg "$PKG" --arg status "$1" --argjson gf "$2" --arg reason "$3" \
        --argjson verify "${4:-null}" --argjson danger "${5:-null}" \
        --arg ch "$CHANNEL" --arg now "$(now_iso)" \
    '{task_id:$pkg.task_id,status:$status,channel:$ch,gate_failed:$gf,
      package:$pkg,
      gate:{verify:$verify,danger:$danger,reason:$reason},
      run:{raw_output:null,exit_code:null,started_at:null,stop_reason:null},
      monitor:null,verdict:null,
      created_at:$now,updated_at:$now}' | atomic_write "$STATE"
}

# ── gate-verify（字段完整性）──
set +e
V_OUT=$(bash "$GATE/gate-verify.sh" --mode package --file "$PKG_TMP" 2>/dev/null); V_RC=$?
set -e
if [[ $V_RC -ne 0 ]]; then
  write_state "created" true "gate-verify 失败: $V_OUT" "$V_OUT" null
  echo "❌ gate-verify 拒绝（exit ${V_RC}）: $V_OUT" >&2
  echo "task_id=$TASK_ID state=$STATE status=created gate_failed=true"
  exit 2
fi
# ── gate-danger（危险/scope/rollback/凭据）──
set +e
D_OUT=$(bash "$GATE/gate-danger.sh" --mode package --file "$PKG_TMP" 2>/dev/null); D_RC=$?
set -e
if [[ $D_RC -ne 0 ]]; then
  write_state "created" true "gate-danger 拦截: $D_OUT" "$V_OUT" "$D_OUT"
  echo "🚫 gate-danger 拦截（exit ${D_RC}）: $D_OUT" >&2
  echo "task_id=$TASK_ID state=$STATE status=created gate_failed=true"
  exit 2
fi
# ── omp 通道可用性（shell 通道）──
if [[ "$CHANNEL" != "acp" ]] && ! omp_available; then
  write_state "created" false "channel_unavailable: omp CLI 未找到（PATH 无 '$OMP_BIN'）" "$V_OUT" "$D_OUT"
  echo "⚠️  channel_unavailable: omp CLI 未找到 → 降级人工复核或 cc-tmux" >&2
  echo "task_id=$TASK_ID state=$STATE status=created channel=unavailable"
  exit 3
fi

# ── 全过 → gated ──
write_state "gated" false "gate 全过：verify ok + danger ok" "$V_OUT" "$D_OUT"
echo "===📋 BEGIN omp-start (relay verbatim)==="
echo "✅ 委派包 gate 全过 → status=gated"
echo "   task_id : $TASK_ID"
echo "   mode    : $(echo "$PKG" | jq -r '.mode')   channel: $CHANNEL"
echo "   criteria: $(echo "$PKG" | jq -r '.criterion | length') 条   risk: $(echo "$PKG" | jq -r '.risk.level')"
echo "   state   : $STATE"
echo "   下一步  : omp-send.sh --state $STATE"
echo "===📋 END==="
echo "task_id=$TASK_ID state=$STATE status=gated"
exit 0
