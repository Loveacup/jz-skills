#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-send.sh —— 四步②：渲染 OMP prompt 并按通道调用 omp
#
# 通道策略（v0.8.0）：RPC 默认 > Shell bounded fallback > ACP 显式实验通道。
#   RPC   : omp --mode rpc 持续连接（NDJSON stdio）；daemon 常驻、fifo 发 prompt、stdout 落盘。
#           天然异步——发 prompt 立即返回，omp-monitor 轮询 turn_end + daemon 心跳。
#   Shell : omp -p --mode json 单次进程（同步/--async）。RPC 启动/就绪失败时自动降级到此。
#   ACP   : 仅在宿主确实提供 ACP adapter 时显式启用；先跑 probe，不假设 delegate_task 支持。
#
# 兼容基线 v16.3.2；RPC/Shell 形态最早在 v16.2.2 实测：
#   RPC  : omp --mode rpc --append-system-prompt <模板> --no-session --tools <白名单> [--cwd][--advisor]
#          stdin: {"type":"prompt","message":"<任务正文>"}  → stdout: 每 turn JSONL（…turn_end）
#   Shell: omp -p --mode json --no-session --max-time N --tools <白名单> [--cwd][--advisor]
#          --append-system-prompt <模板> "<任务正文>"
#   两通道输出同构 JSONL，由 omp-monitor.sh 双层解析（传输层 jq + 应用层内层 JSON）。
#
# 安全默认：缺 capability_grant 时保持只读白名单；显式 v1 grant 仅由 execute package 提供。
#
# 参数：
#   --state <file>     omp-start.sh 写的状态文件（必填）
#   --channel rpc|shell|acp  覆盖委派包通道（默认用委派包 .channel；start 默认 rpc）
#   --max-time <N>     超时秒数（shell=omp --max-time；rpc=holder 存活上限）（默认 300）
#   --async            Shell 通道后台跑（rpc 本就异步，此 flag 对 rpc 无意义）
#   --advisor          附加 omp --advisor（实测 print/rpc 下不注入额外结构，语义见 references）
#   --allow-write      废弃的模糊布尔开关；始终 exit 2，改用版本化 capability_grant
#   --no-auto-approve  关闭 --auto-approve（默认开；只读白名单下安全）
#   --no-fallback      RPC 失败时不降级 Shell（直接报错，便于诊断）
#   --auto-skills      自动路由：审计/审查/架构类任务加载 stdd-omp（默认关）
#   --skills <pats>    指定 OMP --skills 值（逗号分隔 glob，如 stdd-omp,git-*）
#   --no-skills        禁用全部 skills（覆盖 --auto-skills 和 --skills）
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
# bundle_only Shell 审计经资源监督器执行（P0B slice）。可注入 OMP_PY 覆盖解释器。
SUPERVISOR="$SELF_DIR/omp-resource-supervisor.py"
OMP_PY="${OMP_PY:-python3}"
# ── P2B S2：监督型 bundle_only Shell 审计固定走 verdict_v1 capture mode（显式上限，
#   本 slice 不做 env 可控；raw-cap/RLIMIT/async wrapper/sidecars/thinking-control 一律不动）。──
CAPTURE_MODE="verdict_v1"
CAPTURE_INGRESS_CAP=134217728   # 128 MiB：从 stdout 管道实际读入的物理字节上限
CAPTURE_VERDICT_CAP=1048576     # 1 MiB：规范 verdict raw 落盘上限
CAPTURE_DIAGNOSTIC_CAP=524288   # 512 KiB：.diag.jsonl 落盘上限（触顶只截断）

STATE=""; CH_OVERRIDE=""; MAXTIME=300; ASYNC=false; ADVISOR=false; ALLOW_WRITE=false
AUTO_APPROVE=true; DRY=false; FALLBACK=true; SKILLS=""; AUTO_SKILLS=false; NO_SKILLS=false
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
    --auto-skills)     AUTO_SKILLS=true; shift ;;
    --skills)          SKILLS="$2"; shift 2 ;;
    --no-skills)       NO_SKILLS=true; shift ;;
    --dry-run)         DRY=true; shift ;;
    -h|--help)         sed -n '2,46p' "$0"; exit 0 ;;
    *) echo "omp-send: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ "$MAXTIME" =~ ^[1-9][0-9]*$ ]] || { echo "omp-send: --max-time 须为正整数，当前 $MAXTIME" >&2; exit 3; }
[[ -n "$STATE" && -r "$STATE" ]] || { echo "omp-send: 读不到 --state '$STATE'" >&2; exit 2; }

PKG=$(jq -c '.package' "$STATE")
TASK_ID=$(jq -r '.task_id' "$STATE")
require_task_id "$TASK_ID" || exit 3
STATUS=$(jq -r '.status' "$STATE")
CHANNEL=$(jq -r '.channel // "rpc"' "$STATE")
[[ -n "$CH_OVERRIDE" ]] && CHANNEL="$CH_OVERRIDE"
[[ "$STATUS" == "gated" ]] || { echo "omp-send: status=${STATUS}（需 gated 才能发送；先过 omp-start）" >&2; exit 2; }
if $ALLOW_WRITE; then
  echo "omp-send: --allow-write 已隔离停用：请由上层协调 skill 在 execute package 中签发显式 capability_grant" >&2
  exit 2
fi

# 单次 attempt 能力合同：协调层签发，call-omp 只校验并精确映射，不推断角色或授权。
CAP_VALIDATOR="$GATE/resolve-capability-grant.py"
HAS_CAP=$(jq -r '.package | has("capability_grant")' "$STATE")
if [[ "$HAS_CAP" == true ]]; then
  set +e
  CAP_OUT=$(python3 "$CAP_VALIDATOR" --state "$STATE" --phase launch 2>/dev/null); CAP_RC=$?
  set -e
  if [[ "$CAP_RC" -ne 0 ]]; then
    CAP_REASON=$(printf '%s' "$CAP_OUT" | jq -r '.reason // "capability_grant_invalid"' 2>/dev/null || echo capability_grant_invalid)
    echo "omp-send: capability grant 拒绝：$CAP_REASON" >&2
    exit 2
  fi
  CAP=$(printf '%s' "$CAP_OUT" | jq -c '.resolved')
else
  # 旧只读路径不新增 Python 启动依赖，保持原有 supervisor 前置条件与错误合同。
  _legacy_cwd=$(jq -r '.package.scope.cwd // ""' "$STATE")
  CAP=$(jq -cn --arg cwd "$_legacy_cwd" \
    '{present:false,contract:"legacy-readonly",tools:["read","grep","glob","lsp","web_search"],approval:"legacy_auto_approve",cwd:$cwd,add_dirs:[],host_affecting:false}')
  _legacy_fp=$(printf '%s' "$CAP" | shasum -a 256 | awk '{print $1}')
  CAP=$(printf '%s' "$CAP" | jq -c --arg fp "$_legacy_fp" '.fingerprint=$fp')
fi
CAP_PRESENT=$(printf '%s' "$CAP" | jq -r '.present')
CAP_CONTRACT=$(printf '%s' "$CAP" | jq -r '.contract')
CAP_FINGERPRINT=$(printf '%s' "$CAP" | jq -r '.fingerprint')
CAP_TOOLS=$(printf '%s' "$CAP" | jq -r '.tools | join(",")')
CAP_CWD=$(printf '%s' "$CAP" | jq -r '.cwd // ""')
CAP_ADD_DIRS=()
while IFS= read -r _cap_dir; do [[ -n "$_cap_dir" ]] && CAP_ADD_DIRS+=("$_cap_dir"); done \
  < <(printf '%s' "$CAP" | jq -r '.add_dirs[]?')
if [[ "$CAP_PRESENT" == true && "$AUTO_APPROVE" != true ]]; then
  echo "omp-send: 显式 capability grant 与 --no-auto-approve 冲突；非交互通道不会猜测审批语义" >&2
  exit 2
fi
if [[ "$CAP_PRESENT" == true && "$CHANNEL" != "shell" ]]; then
  echo "omp-send: capability grant v1 仅支持 Shell；RPC 缺可信的单 attempt exit code，ACP 尚不能保真传递 grant" >&2
  exit 2
fi
# 显式 grant 只使用版本化 approval-mode；legacy --auto-approve 不叠加。
if [[ "$CAP_PRESENT" == true ]]; then AUTO_APPROVE=false; fi

# ── bundle_only 检测：仅 Shell 通道启用资源监督 + 强制 async 安全默认 ──
# RPC / ACP 语义保持不变（含 RPC 失败降级 shell 的路径——那属于 RPC 通道行为）。
INDEP=$(echo "$PKG" | jq -r '.auditor.independence_level // ""')
BUNDLE_ONLY=false; SUPERVISED=false
[[ "$INDEP" == "bundle_only" ]] && BUNDLE_ONLY=true
if $BUNDLE_ONLY && [[ "$CHANNEL" == "shell" ]]; then
  SUPERVISED=true
  if ! $ASYNC; then
    ASYNC=true
    echo "🛡  omp-send: bundle_only Shell 审计 → 已强制 --async + 资源监督（安全默认已启用，忽略同步调用）" >&2
  fi
fi

# ── 智能技能路由（--auto-skills）──
# 检查指定 OMP skill 是否存在（参数：skill 名，如 stdd-omp）
omp_skill_available() {
  local sk="$1"
  # 优先靠 omp --list-skills（若有）
  if command -v omp >/dev/null 2>&1 && omp --list-skills 2>/dev/null | grep -qw "$sk"; then
    return 0
  fi
  # 降级：检查文件系统已知路径
  for d in ~/.omp/skills ~/.config/omp/skills /usr/local/share/omp/skills; do
    [[ -f "$d/$sk/SKILL.md" ]] && return 0
  done
  return 1
}

route_skills() {
  local task="$1"
  if [[ -z "$task" ]]; then return; fi
  # 高信号关键词 → STDD 审计（收紧：去掉"验证""检查"过宽词，"review"加词边界）
  if echo "$task" | grep -qiE '审计|审查|\breview\b|架构|安全|合规|验收|bug|缺陷|漏洞|STDD|承重墙|BLOCKER|evidence|反幻觉'; then
    if omp_skill_available "stdd-omp"; then
      echo "stdd-omp"
    else
      warn "auto-skills: stdd-omp 不可用，降级为 plain OMP"
    fi
  fi
}

if $NO_SKILLS; then
  SKILLS=""
elif $AUTO_SKILLS && [[ -z "$SKILLS" ]]; then
  TASK=$(echo "$PKG" | jq -r '.task')
  SKILLS=$(route_skills "$TASK")
  [[ -n "$SKILLS" ]] && echo "   🧠 auto-skills → $SKILLS" >&2
fi

update_state() { local f="$1"; local s; s=$(jq "$f | .updated_at=\"$(now_iso)\"" "$STATE"); printf '%s' "$s" | atomic_write "$STATE"; }

# ── P2A-static：显式可信 OMP_BUNDLE_THINKING（无运行时能力探测）───────────────
# 契约：未设/空/inherit → 继承（永不加 --thinking argv）；off → 仅【监督型 bundle_only Shell】
#   实际执行时注入精确 `--thinking off` 并持久化 run.thinking_control。
#   任何其它非空值属 operator 配置错误：在任何子进程 / 资源 sidecar 之前 exit 3 且记录明确原因，
#   绝不静默纠正。这是可见的运维决策，不做能力发现 / 探测 / 回退。
BUNDLE_THINKING="${OMP_BUNDLE_THINKING:-inherit}"
[[ -z "$BUNDLE_THINKING" ]] && BUNDLE_THINKING="inherit"
case "$BUNDLE_THINKING" in
  inherit|off) ;;
  *)
    _bt_s=$(jq --arg v "$BUNDLE_THINKING" --arg ts "$(now_iso)" \
      '.status="rejected" | .gate.reason=("channel_error: operator-config OMP_BUNDLE_THINKING 非法值 "+$v+"（仅接受 off｜inherit｜未设）") | .updated_at=$ts' "$STATE")
    printf '%s' "$_bt_s" | atomic_write "$STATE"
    echo "🚫 omp-send: OMP_BUNDLE_THINKING='$BUNDLE_THINKING' 非法（operator-config；仅 off|inherit|未设）→ exit 3" >&2
    exit 3 ;;
esac

# ── gate-counter：本次 send = 一轮 ──
set +e
C_ERR=$(mktemp)
C_OUT=$(bash "$GATE/gate-counter.sh" --task-id "$TASK_ID" --inc-round \
        --round-limit "$(echo "$PKG" | jq -r '.threshold.round_limit')" \
        --reject-limit "$(echo "$PKG" | jq -r '.threshold.reject_limit')" 2>"$C_ERR"); C_RC=$?
[[ $C_RC -ne 0 && $C_RC -ne 20 ]] && { echo "⚠ gate-counter 异常 (rc=$C_RC):" >&2; cat "$C_ERR" >&2; }
rm -f "$C_ERR"
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
[[ "$CAP_PRESENT" == true ]] && CWD="$CAP_CWD"
ALLOWED=$(echo "$PKG" | jq -rc '.scope.allowed_paths // []')
DENIED=$(echo "$PKG" | jq -rc '.scope.denied_paths // []')
CRIT_LIST=$(echo "$PKG" | jq -r '.criterion[] | "  - " + .')
RL=$(echo "$PKG" | jq -r '.threshold.round_limit')
JL=$(echo "$PKG" | jq -r '.threshold.reject_limit')

# 关键字段空值校验
[[ -z "$TASK" || "$TASK" == "null" ]] && { echo "omp-send: 委派包 .task 缺失或为空" >&2; exit 3; }
[[ -z "$MODE_FULL" || "$MODE_FULL" == "null" ]] && { echo "omp-send: 委派包 .mode 缺失" >&2; exit 3; }
[[ "$RL" =~ ^[0-9]+$ ]] || RL=3
[[ "$JL" =~ ^[0-9]+$ ]] || JL=3

case "$BASE_MODE" in
  govern) TPL="$TPL_DIR/govern-prompt-template.md" ;;
  execute) TPL="$TPL_DIR/execute-prompt-template.md" ;;
  *) TPL="$TPL_DIR/audit-prompt-template.md" ;;
esac
if [[ -r "$TPL" ]]; then SYS=$(cat "$TPL"); else
  SYS="你是独立审查者。只输出一个 JSON 对象（可包在 \`\`\`json 围栏里），字段：severity(nit|concern|blocker|pass)、summary、evidence(数组，每项 {type,ref} 指真实文件/命令/行号；不得为空)、reject_instruction。不采信无证据的结论。"
fi

CAPABILITY_DESC=$(printf '%s' "$CAP" | jq -c '{contract,tools,approval,cwd,add_dirs,host_affecting}')
if [[ "$BASE_MODE" == execute ]]; then
  OUTPUT_RULES=$(cat <<EOF
  - 这是通用执行任务，不套审计 verdict schema；按 execute system prompt 自由汇报。
  - 只能使用启动层实际授予的 capability；grant 不是 OS sandbox，scope 仍是任务合同。
  - 启动 capability：$CAPABILITY_DESC
  - 本任务轮次上限 ${RL}、reject 上限 ${JL}；不要绕过 scope。
EOF
)
else
  OUTPUT_RULES=$(cat <<EOF
  - 严格按 system 提示的 JSON schema 输出，允许字段仅 required_actions_contract / severity / summary / evidence / reject_instruction / required_actions / confidence。
  - evidence 必须是真实的文件路径+行号 / 命令+输出 / 测试结果，禁止空数组、禁止只写自然语言总结。
  - 本任务轮次上限 ${RL}、reject 上限 ${JL}；不要绕过 scope。
EOF
)
fi

USER_MSG=$(cat <<EOF
[OMP 委派任务 · task_id=$TASK_ID · mode=$MODE_FULL · 第 $ROUND 轮]

任务：
$TASK

scope（严格遵守，越界即视为失败）：
  允许路径：$ALLOWED
  禁止路径：$DENIED
  工作目录：${CWD:-（未指定，默认当前）}
$([ -n "$SUBMODE" ] && printf '治理子模式：%s\n' "$SUBMODE")

可裁决验收条件（逐条核对）：
$CRIT_LIST

约束：
$OUTPUT_RULES
EOF
)

# ── 版本化 capability grant → OMP 原生工具/审批参数 ──
TOOLS="$CAP_TOOLS"
APPROVAL_MODE=""
if [[ "$CAP_PRESENT" == true ]]; then APPROVAL_MODE="yolo"; fi
CAP_ADD_DIRS_JSON=$(printf '%s' "$CAP" | jq -c '.add_dirs')
SYSTEM_HASH=$(printf '%s' "$SYS" | shasum -a 256 | awk '{print $1}')
OMP_CMD_PATH=$(command -v "$OMP_BIN" 2>/dev/null || true)
OMP_CMD_CANON=""; OMP_CMD_SHA=""
if [[ -n "$OMP_CMD_PATH" && -f "$OMP_CMD_PATH" ]]; then
  OMP_CMD_CANON=$(perl -MCwd=realpath -e 'print realpath($ARGV[0]) // $ARGV[0]' "$OMP_CMD_PATH" 2>/dev/null || printf '%s' "$OMP_CMD_PATH")
  OMP_CMD_SHA=$(shasum -a 256 "$OMP_CMD_PATH" 2>/dev/null | awk '{print $1}')
fi
LAUNCH_SPEC=$(jq -cn \
  --arg cap "$CAP_FINGERPRINT" --arg tools "$TOOLS" --arg approval "$APPROVAL_MODE" \
  --arg cwd "$CWD" --argjson add_dirs "$CAP_ADD_DIRS_JSON" --arg skills "$SKILLS" \
  --argjson advisor "$ADVISOR" --argjson auto_approve "$AUTO_APPROVE" --arg system_hash "$SYSTEM_HASH" \
  --arg omp_bin_requested "$OMP_BIN" --arg omp_bin_path "$OMP_CMD_CANON" --arg omp_bin_sha256 "$OMP_CMD_SHA" \
  '{capability_fingerprint:$cap,tools:$tools,approval_mode:$approval,cwd:$cwd,add_dirs:$add_dirs,skills:$skills,advisor:$advisor,auto_approve:$auto_approve,system_hash:$system_hash,omp_bin_requested:$omp_bin_requested,omp_bin_path:$omp_bin_path,omp_bin_sha256:$omp_bin_sha256}')
LAUNCH_FINGERPRINT=$(printf '%s' "$LAUNCH_SPEC" | shasum -a 256 | awk '{print $1}')

RAW="$(raw_path "$TASK_ID")"; PROMPT="$(prompt_path "$TASK_ID")"
printf '%s\n' "$USER_MSG" | atomic_write "$PROMPT"

# ── dry-run：只渲染不发 ──
if $DRY; then
  echo "===📋 BEGIN omp-send --dry-run (relay verbatim)==="
  echo "channel=$CHANNEL  task_id=$TASK_ID  mode=$MODE_FULL  round=$ROUND  tools=$TOOLS  approval=${APPROVAL_MODE:-legacy}  max-time=$MAXTIME  skills=${SKILLS:-(none)}"
  echo "capability_contract=$CAP_CONTRACT  capability_fingerprint=$CAP_FINGERPRINT  launch_fingerprint=$LAUNCH_FINGERPRINT"
  if [[ "$CHANNEL" == "rpc" ]]; then
    echo "rpc daemon: $OMP_BIN --mode rpc --no-session --tools $TOOLS ${SKILLS:+--skills "$SKILLS"} ${CWD:+--cwd "$CWD"} ${AUTO_APPROVE:+--auto-approve}${ADVISOR:+ --advisor} --append-system-prompt <sys>"
    echo "rpc stdin : $(jq -cn --arg m "$USER_MSG" '{type:"prompt",message:$m}' | head -c 160)…"
  elif $SUPERVISED; then
    echo "mode      : bundle_only → 强制 --async + 资源监督（omp-resource-supervisor.py，无同步回退）"
    echo "capture   : verdict_v1（--capture-mode ${CAPTURE_MODE} --ingress-cap ${CAPTURE_INGRESS_CAP} --verdict-cap ${CAPTURE_VERDICT_CAP} --diagnostic-cap ${CAPTURE_DIAGNOSTIC_CAP}）· diag=$RAW.diag.jsonl"
    echo "supervisor: $OMP_PY $SUPERVISOR --state-file $(resource_state_path "$TASK_ID") --raw-output $RAW --pid-store $(pid_store_path "$TASK_ID") --task-id $TASK_ID --capture-mode $CAPTURE_MODE --ingress-cap $CAPTURE_INGRESS_CAP --verdict-cap $CAPTURE_VERDICT_CAP --diagnostic-cap $CAPTURE_DIAGNOSTIC_CAP -- $OMP_BIN -p --mode json --no-session --max-time $MAXTIME --tools $TOOLS ${SKILLS:+--skills \"$SKILLS\"} ${CWD:+--cwd \"$CWD\"} … --append-system-prompt <sys> <user_msg>"
    echo "将持久化  : run.resource_supervised=true · run.watch_required=true · run.mode=async · run.capture_mode=verdict_v1 · run.diagnostic_output · run.resource_state · run.pid_store · wrapper pid"
  else
    echo "shell cmd : $OMP_BIN -p --mode json --no-session --max-time $MAXTIME --tools $TOOLS ${SKILLS:+--skills \"$SKILLS\"} ${CWD:+--cwd \"$CWD\"} … --append-system-prompt <sys> <user_msg>"
  fi
  echo "--- 渲染的任务正文（${PROMPT}）---"; printf '%s\n' "$USER_MSG"
  echo "===📋 END（dry-run 未调用 omp）==="
  exit 0
fi

# 发送前持久化解析后的 attempt 合同；启动失败也保留真实 forensic，且不得改写 grant。
_cap_state=$(jq --argjson cap "$CAP" --arg capfp "$CAP_FINGERPRINT" \
  --arg launchfp "$LAUNCH_FINGERPRINT" --argjson launch "$LAUNCH_SPEC" \
  --arg now "$(now_iso)" \
  '.run.capability=$cap | .run.capability_fingerprint=$capfp |
   .run.launch_fingerprint=$launchfp | .run.launch_spec=$launch | .updated_at=$now' "$STATE")
printf '%s\n' "$_cap_state" | atomic_write "$STATE"

# ── P2A-static：无探测。thinking 控制完全来自脚本顶部校验过的 OMP_BUNDLE_THINKING，
#   仅在【监督型 bundle_only Shell】实际执行边界应用（见 shell_send）。此处不再有任何
#   --help 能力发现 / tempfile / Python helper——那条 provider 探测路径已按 L2 决策移除。

# ════ Shell 通道（也是 RPC 的降级目标）════════════════════════════
shell_send() {
  if ! omp_available; then
    update_state ".status=\"rejected\" | .gate.reason=\"channel_error: omp CLI 不存在\""
    echo "🚫 omp-send: omp 不可用 → status=rejected (channel_error)" >&2; return 3
  fi
  # bundle_only 不变量：在【实际执行边界】强制监督，而非只看初始通道选择。
  # 无论是直连 Shell 还是 RPC 失败降级到此，只要是 bundle_only 就必须
  # 资源监督 + 强制 async + watch_required——杜绝降级路径逃逸到无监督同步 Shell。
  if $BUNDLE_ONLY && ! $SUPERVISED; then
    SUPERVISED=true; ASYNC=true
    echo "🛡  omp-send: bundle_only 经 Shell 执行（RPC 降级路径）→ 已强制 --async + 资源监督（安全默认）" >&2
  fi
  # ── P2A-static：仅【监督型 bundle_only Shell】按显式 OMP_BUNDLE_THINKING 注入 --thinking ──
  # 覆盖直连监督 Shell 与 RPC→Shell 降级（降级已在上面重入监督）。非监督路径 THINKING_CTL 恒空 →
  # 零改动、零 thinking 状态。配置已在脚本顶部校验，此处不做任何探测 / 能力发现。
  local THINKING_CTL=""
  $SUPERVISED && THINKING_CTL="$BUNDLE_THINKING"
  local args=(-p --mode json --no-session --max-time "$MAXTIME" --tools "$TOOLS")
  [[ -n "$APPROVAL_MODE" ]] && args+=(--approval-mode "$APPROVAL_MODE")
  [[ "$THINKING_CTL" == "off" ]] && args+=(--thinking off)
  [[ -n "$SKILLS" ]] && args+=(--skills "$SKILLS")
  $AUTO_APPROVE && args+=(--auto-approve)
  [[ -n "$CWD" ]] && args+=(--cwd "$CWD")
  local _add_dir
  for _add_dir in "${CAP_ADD_DIRS[@]:-}"; do [[ -n "$_add_dir" ]] && args+=(--add-dir "$_add_dir"); done
  $ADVISOR && args+=(--advisor)
  args+=(--append-system-prompt "$SYS" "$USER_MSG")

  # ── bundle_only：只经资源监督器异步跑 OMP（强制 async，杜绝同步回退）──
  if $SUPERVISED; then
    if [[ ! -r "$SUPERVISOR" ]] || ! command -v "${OMP_PY%% *}" >/dev/null 2>&1; then
      update_state ".status=\"rejected\" | .gate.reason=\"channel_error: bundle_only 需资源监督器，但 python3/supervisor 不可用（不回退同步）\""
      echo "🚫 omp-send: bundle_only 资源监督器不可用（$OMP_PY / ${SUPERVISOR}）→ status=rejected" >&2; return 3
    fi
    local rstate pids diag
    rstate="$(resource_state_path "$TASK_ID")"; pids="$(pid_store_path "$TASK_ID")"
    # verdict_v1 诊断 sidecar 由监督器派生自 raw_output（raw + ".diag.jsonl"）；此处仅镜像入主状态。
    diag="$RAW.diag.jsonl"
    rm -f "$RAW.exit"
    # wrapper 子壳：跑 supervisor，落其退出码到 .exit sidecar（0 正常 / 2 资源拒绝 / 等）。
    # supervisor 自行把子进程 stdout 流式分帧分类写入 canonical verdict raw；此处只收 supervisor 自身 stderr。
    ( set +e
      "$OMP_PY" "$SUPERVISOR" \
        --state-file "$rstate" --raw-output "$RAW" --pid-store "$pids" \
        --task-id "$TASK_ID" --task-id-source call-omp-send \
        --capture-mode "$CAPTURE_MODE" \
        --ingress-cap "$CAPTURE_INGRESS_CAP" \
        --verdict-cap "$CAPTURE_VERDICT_CAP" \
        --diagnostic-cap "$CAPTURE_DIAGNOSTIC_CAP" \
        -- "$OMP_BIN" "${args[@]}" >/dev/null 2>"$RAW.err" </dev/null
      _ec=$?; printf '%s\n' "$_ec" | atomic_write "$RAW.exit" ) &
    local pid=$!; disown 2>/dev/null || true
    # 单次原子写：主任务状态仍是 call-omp 状态 schema，补资源监督字段 + verdict_v1 capture 字段。
    update_state ".status=\"running\" | .run.channel_used=\"shell\" | .run.mode=\"async\" | .run.raw_output=\"$RAW\" | .run.resource_state=\"$rstate\" | .run.pid_store=\"$pids\" | .run.resource_supervised=true | .run.watch_required=true | .run.capture_mode=\"$CAPTURE_MODE\" | .run.diagnostic_output=\"$diag\" | .run.thinking_control=\"$THINKING_CTL\" | .run.pid=$pid | .run.round=$ROUND | .run.started_at=\"$(now_iso)\""
    echo "===📋 BEGIN omp-send shell bundle_only supervised --async (relay verbatim)==="
    echo "🛡  bundle_only 安全默认已强制：--async + 资源监督（raw_cap 熔断，无同步回退）"
    echo "🚀 已后台发起 OMP（第 $ROUND 轮，经 supervisor）· wrapper pid=$pid"
    echo "   raw           : $RAW"
    echo "   resource_state: $rstate"
    echo "   pid_store     : $pids"
    echo "   监控: omp-monitor.sh --state $STATE   · 干预: kill $pid"
    echo "===📋 END==="; return 0
  fi

  update_state ".status=\"running\" | .run.channel_used=\"shell\" | .run.raw_output=\"$RAW\" | .run.started_at=\"$(now_iso)\" | .run.round=$ROUND"
  if $ASYNC; then
    rm -f "$RAW.exit"
    if command -v perl >/dev/null 2>&1; then
      ( set +e; perl -e 'alarm shift; exec @ARGV or exit 127' "$((MAXTIME + 30))" "$OMP_BIN" "${args[@]}" >"$RAW" 2>"$RAW.err" </dev/null; _ec=$?; printf '%s\n' "$_ec" | atomic_write "$RAW.exit" ) &
    else
      ( set +e; "$OMP_BIN" "${args[@]}" >"$RAW" 2>"$RAW.err" </dev/null; _ec=$?; printf '%s\n' "$_ec" | atomic_write "$RAW.exit" ) &
    fi
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
  # 复用存活 daemon 前校验完整启动指纹（防 cwd/skills/system/binary 漂移）
  if [[ -n "$dpid" ]]; then
    REC_FP=$(jq -r '.run.rpc_launch_fingerprint // ""' "$STATE")
    if [[ "$REC_FP" != "$LAUNCH_FINGERPRINT" ]]; then
      warn "rpc: daemon 启动指纹不匹配，重启"
      rpc_stop "$TASK_ID" "$dpid" "$hpid"
      dpid=""; hpid=""
    fi
  fi
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
    [[ -n "$SKILLS" ]] && dargs+=(--skills "$SKILLS")
    $AUTO_APPROVE && dargs+=(--auto-approve)
    [[ -n "$APPROVAL_MODE" ]] && dargs+=(--approval-mode "$APPROVAL_MODE")
    [[ -n "$CWD" ]] && dargs+=(--cwd "$CWD")
    local _rpc_add_dir
    for _rpc_add_dir in "${CAP_ADD_DIRS[@]:-}"; do [[ -n "$_rpc_add_dir" ]] && dargs+=(--add-dir "$_rpc_add_dir"); done
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
    update_state ".run.rpc_pid=$dpid | .run.holder_pid=$hpid | .run.fifo=\"$fifo\" | .run.rpc_tools=\"$TOOLS\" | .run.rpc_auto_approve=\"$AUTO_APPROVE\" | .run.rpc_launch_fingerprint=\"$LAUNCH_FINGERPRINT\""
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
    # .run.omp_skills: Hermes 读取后传给 delegate_task 的 acp_args（如 --skills=stdd-omp）
    # ACP: spawn OMP as sub-agent via delegate_task(acp_command='omp').
    # omp acp starts ACP server over stdio; prompt delivered via ACP protocol.
    # This script prepares state; Hermes reads it and calls delegate_task.
    update_state ".status=\"pending_acp\" | .run.channel_used=\"acp\" | .run.omp_skills=\"${SKILLS:-}\" | .run.mode=\"acp\" | .run.prompt=\"$PROMPT\" | .run.raw_output=\"$RAW\" | .run.task=\"$TASK\" | .run.started_at=\"$(now_iso)\" | .run.round=$ROUND"
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
