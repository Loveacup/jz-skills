#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# run-all.sh —— omp skill 自包含测试套件（gate 硬卡 + 四步状态机端到端）
#
# 用 OMP_BIN 注入 mock omp（不烧真 token）、OMP_TMPDIR 注入临时目录（隔离）。
# 覆盖验收标准：gate 硬卡（exit 10/20）、start→send→monitor→finish 全链、
#              blocker/空证据红线、async 监控+干预、channel_unavailable、gc 保护 running。
#
# 用法： bash tests/run-all.sh        退出码 0=全过，非 0=有失败
# ─────────────────────────────────────────────────────────────────
set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"; S="$SKILL_DIR/scripts"
TD="${TMPDIR:-/tmp}/omp-selftest-$$"; rm -rf "$TD"; mkdir -p "$TD"
export OMP_TMPDIR="$TD"
trap 'rm -rf "$TD"' EXIT
HOT_START_BEFORE=$(shasum "$S/omp-start.sh" | awk '{print $1}')
HOT_SEND_BEFORE=$(shasum "$S/omp-send.sh" | awk '{print $1}')

P=0; F=0
chk(){ if [[ "$2" == "$3" ]]; then echo "  ✅ $1"; P=$((P+1)); else echo "  ❌ $1 exp=[$2] got=[$3]"; F=$((F+1)); fi; }

# ── mocks ──
cat > "$TD/mock-omp.sh" <<'M'
#!/usr/bin/env bash
cat <<'J'
{"type":"session","id":"m1"}
{"type":"message_end","message":{"role":"assistant","content":[{"type":"thinking","thinking":"x"},{"type":"text","text":"审计完成\n```json\n{\"severity\":\"concern\",\"summary\":\"发现拼接 SQL\",\"evidence\":[{\"type\":\"file\",\"ref\":\"auth.ts:42\"}],\"reject_instruction\":\"参数化\",\"confidence\":\"high\"}\n```"}]}}
{"type":"turn_end","message":{"role":"assistant","stopReason":"stop","content":[{"type":"text","text":"done"}],"usage":{"totalTokens":100}}}
J
M
cat > "$TD/mock-blocker.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"blocker\",\"summary\":\"明文密码\",\"evidence\":[{\"type\":\"file\",\"ref\":\"db.ts:88\"}],\"reject_instruction\":\"bcrypt\"}\n```"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
cat > "$TD/mock-noev.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"pass\",\"summary\":\"ok\",\"evidence\":[]}\n```"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
cat > "$TD/mock-slow.sh" <<'M'
#!/usr/bin/env bash
echo '{"type":"session","id":"s"}'; sleep 6; echo '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
chmod +x "$TD"/mock-*.sh
export OMP_BIN="$TD/mock-omp.sh"

GP='{"channel":"shell","mode":"audit","task":"审查 auth","scope":{"allowed_paths":["src/auth"],"denied_paths":[],"cwd":"/tmp/repo"},"criterion":["SQL 参数化"],"threshold":{"round_limit":3,"reject_limit":2},"risk":{"level":"low","dangerous_modes":[]},"auditor":{"required":true,"independence_level":"independent_readonly"},"output":{"format":"json","evidence_required":true}}'
mkpkg(){ echo "$GP" | jq "$@"; }

echo "═══ 1. gate-verify ═══"
mkpkg '.task_id="t-ok"' > "$TD/pkg-ok.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-ok.json" >/dev/null 2>&1; chk "package 齐全→0" 0 $?
mkpkg '.task_id="t-ok"|.criterion=[]' > "$TD/pkg-noc.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-noc.json" >/dev/null 2>&1; chk "缺 criterion→1" 1 $?
for bad_id in '../escape' '/abs' 'a/b'; do
  mkpkg --arg id "$bad_id" '.task_id=$id' > "$TD/pkg-bad-id.json"
  bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-bad-id.json" >/dev/null 2>&1; chk "非法 task_id=${bad_id}→1" 1 $?
  bash "$S/omp-start.sh" --mode execute --channel acp --task x --task-id "$bad_id" >/dev/null 2>&1; chk "start 拒绝 task_id=${bad_id}→3" 3 $?
  bash "$S/gate/gate-counter.sh" --task-id "$bad_id" --inc-round >/dev/null 2>&1; chk "counter 拒绝 task_id=${bad_id}→3" 3 $?
done
LONG_ID=$(printf 'a%.0s' {1..129})
mkpkg --arg id "$LONG_ID" '.task_id=$id' > "$TD/pkg-long-id.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-long-id.json" >/dev/null 2>&1; chk "129字符 task_id→1" 1 $?
"$TD/mock-omp.sh" > "$TD/raw-ok.json"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-ok.json" >/dev/null 2>&1; chk "output 有 evidence→0" 0 $?
"$TD/mock-noev.sh" > "$TD/raw-noev.json"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-noev.json" >/dev/null 2>&1; chk "output 空 evidence→10" 10 $?

echo "═══ 2. gate-danger ═══"
bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-ok.json" >/dev/null 2>&1; chk "安全包→0" 0 $?
for gm in clean deep-clean sql; do
  mkpkg ".mode=\"govern:$gm\"|.scope={allowed_paths:[],denied_paths:[],cwd:\"\"}|.risk={level:\"low\",dangerous_modes:[]}" > "$TD/pkg-gov-$gm-noscope.json"
  bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-gov-$gm-noscope.json" >/dev/null 2>&1; chk "govern:$gm 无 scope/rollback→10" 10 $?
  mkpkg ".mode=\"govern:$gm\"|.scope.cwd=\"/tmp/repo\"|.risk={level:\"high\",dangerous_modes:[],rollback:\"restore backup\"}" > "$TD/pkg-gov-$gm-ok.json"
  bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-gov-$gm-ok.json" >/dev/null 2>&1; chk "govern:$gm 有 scope+rollback→0" 0 $?
  mkpkg ".mode=\"govern:$gm\"|.scope.cwd=\"/tmp/repo\"|.risk={level:\"low\",dangerous_modes:[],rollback:\"restore backup\"}" > "$TD/pkg-gov-$gm-low.json"
  bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-gov-$gm-low.json" >/dev/null 2>&1; chk "govern:$gm risk=low→10" 10 $?
done
mkpkg '.mode="govern:clean"|.scope={allowed_paths:[""],denied_paths:[],cwd:" "}|.risk={level:"high",dangerous_modes:[],rollback:"   "}' > "$TD/pkg-gov-blank.json"
bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-gov-blank.json" >/dev/null 2>&1; chk "govern 空白 scope/rollback→10" 10 $?
bash "$S/gate/gate-danger.sh" --mode prompt --scan-text "rm -rf /data" >/dev/null 2>&1; chk "prompt rm-rf→10" 10 $?
bash "$S/gate/gate-danger.sh" --mode prompt --scan-text "password: hunter2abc" >/dev/null 2>&1; chk "凭据→10" 10 $?

echo "═══ 3. gate-counter ═══"
bash "$S/gate/gate-counter.sh" --task-id c1 --inc-round >/dev/null 2>&1
bash "$S/gate/gate-counter.sh" --task-id c1 --inc-round >/dev/null 2>&1
bash "$S/gate/gate-counter.sh" --task-id c1 --inc-round >/dev/null 2>&1; chk "round 第3→0" 0 $?
bash "$S/gate/gate-counter.sh" --task-id c1 --inc-round >/dev/null 2>&1; chk "round 第4→20" 20 $?
bash "$S/gate/gate-counter.sh" --task-id c2 --inc-reject >/dev/null 2>&1
bash "$S/gate/gate-counter.sh" --task-id c2 --inc-reject >/dev/null 2>&1; chk "reject 第2→0" 0 $?
bash "$S/gate/gate-counter.sh" --task-id c2 --inc-reject >/dev/null 2>&1; chk "reject 第3→20" 20 $?

echo "═══ 4. 端到端 accept ═══"
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id f1 >/dev/null 2>&1; chk "start→gated" 0 $?
chk "  状态 gated" gated "$(jq -r .status "$TD/omp-state-f1.json")"
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-f1.json" >/dev/null 2>&1; chk "send→0" 0 $?
bash "$S/omp-monitor.sh" --state "$TD/omp-state-f1.json" >/dev/null 2>&1; chk "monitor→reported" 0 $?
chk "  severity=concern" concern "$(jq -r .monitor.severity "$TD/omp-state-f1.json")"
chk "  evidence=1" 1 "$(jq -r .monitor.evidence_count "$TD/omp-state-f1.json")"
bash "$S/omp-finish.sh" --state "$TD/omp-state-f1.json" --accept >/dev/null 2>&1; chk "finish accept→0" 0 $?
chk "  状态 accepted" accepted "$(jq -r .status "$TD/omp-state-f1.json")"
[[ -f "$TD/omp-archive/f1/verdict.yaml" ]] && chk "  归档 verdict" y y || chk "  归档 verdict" y n
grep -q 'next_action: accept' "$TD/omp-archive/f1/verdict.yaml" 2>/dev/null && chk "  verdict next_action" y y || chk "  verdict next_action" y n

echo "═══ 5. blocker 红线 + reject ═══"
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id f2 >/dev/null 2>&1
OMP_BIN="$TD/mock-blocker.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-f2.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-f2.json" >/dev/null 2>&1
chk "  severity=blocker" blocker "$(jq -r .monitor.severity "$TD/omp-state-f2.json")"
bash "$S/omp-finish.sh" --state "$TD/omp-state-f2.json" --accept >/dev/null 2>&1; chk "accept blocker→拒绝(2)" 2 $?
bash "$S/omp-finish.sh" --state "$TD/omp-state-f2.json" --reject >/dev/null 2>&1; chk "reject→0" 0 $?
chk "  状态 rejected" rejected "$(jq -r .status "$TD/omp-state-f2.json")"

echo "═══ 6. 空证据监控拒绝 ═══"
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id f3 >/dev/null 2>&1
OMP_BIN="$TD/mock-noev.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-f3.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-f3.json" >/dev/null 2>&1; chk "monitor 空证据→10" 10 $?
chk "  状态 rejected" rejected "$(jq -r .status "$TD/omp-state-f3.json")"

echo "═══ 7. async 监控 + 干预 ═══"
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id f4 >/dev/null 2>&1
OMP_BIN="$TD/mock-slow.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-f4.json" --async --max-time 30 >/dev/null 2>&1; chk "async send→0" 0 $?
PID=$(jq -r '.run.pid' "$TD/omp-state-f4.json")
MJ=$(bash "$S/omp-monitor.sh" --state "$TD/omp-state-f4.json" --json 2>/dev/null)
chk "  进行中 phase=running" running "$(echo "$MJ" | jq -r .phase 2>/dev/null)"
echo "$MJ" | jq -e . >/dev/null 2>&1 && chk "  进行中 JSON 合法" y y || chk "  进行中 JSON 合法" y n
kill "$PID" 2>/dev/null; chk "  kill 干预" 0 $?

echo "═══ 8. channel_unavailable + dry-run + gc ═══"
echo "$GP" | OMP_BIN=/nonexistent bash "$S/omp-start.sh" --package-json - --task-id f5 >/dev/null 2>&1; chk "omp 缺失→3" 3 $?
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id f6 >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-f6.json" --dry-run >/dev/null 2>&1; chk "dry-run→0" 0 $?
chk "  dry-run 仍 gated" gated "$(jq -r .status "$TD/omp-state-f6.json")"
bash "$S/omp-gc.sh" --mode scan >/dev/null 2>&1; chk "gc scan→0" 0 $?

echo "═══ 9. --help 契约 ═══"
for sc in omp-start omp-send omp-monitor omp-finish omp-gc; do
  bash "$S/$sc.sh" --help >/dev/null 2>&1; chk "$sc --help" 0 $?
done
for g in gate-verify gate-danger gate-counter; do
  bash "$S/gate/$g.sh" --help >/dev/null 2>&1; chk "$g --help" 0 $?
done

echo "═══ 10. RPC 通道（mock daemon：toolUse turn + stop turn）═══"
cat > "$TD/mock-rpc.sh" <<'M'
#!/usr/bin/env bash
echo '{"type":"ready"}'
while IFS= read -r _l; do
  printf '%s\n' \
'{"type":"turn_start"}' \
'{"type":"turn_end","message":{"role":"assistant","stopReason":"toolUse","content":[{"type":"toolCall"}]}}' \
'{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"concern\",\"summary\":\"mock rpc audit\",\"evidence\":[{\"type\":\"file\",\"ref\":\"x.js:1\"}]}\n```"}]}}' \
'{"type":"turn_end","message":{"role":"assistant","stopReason":"stop","content":[{"type":"text","text":"done"}]}}'
done
M
chmod +x "$TD/mock-rpc.sh"
echo "$GP" | jq '.channel="rpc"' | bash "$S/omp-start.sh" --package-json - --task-id rpc1 >/dev/null 2>&1
chk "rpc start channel=rpc" rpc "$(jq -r .channel "$TD/omp-state-rpc1.json")"
OMP_BIN="$TD/mock-rpc.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-rpc1.json" --max-time 30 >/dev/null 2>&1
chk "rpc send channel_used=rpc" rpc "$(jq -r .run.channel_used "$TD/omp-state-rpc1.json")"
RP=""
for i in $(seq 1 30); do
  bash "$S/omp-monitor.sh" --state "$TD/omp-state-rpc1.json" --json >"$TD/rmon.json" 2>/dev/null
  RP=$(jq -r .phase "$TD/rmon.json" 2>/dev/null)
  [[ "$RP" != "running" ]] && break; sleep 0.5
done
chk "rpc monitor→reported" reported "$RP"
chk "rpc severity=concern" concern "$(jq -r .monitor.severity "$TD/omp-state-rpc1.json")"
RDPID=$(jq -r .run.rpc_pid "$TD/omp-state-rpc1.json")
bash "$S/omp-finish.sh" --state "$TD/omp-state-rpc1.json" --human-review >/dev/null 2>&1
chk "rpc finish 停 daemon" stopped "$(kill -0 "$RDPID" 2>/dev/null && echo alive || echo stopped)"

cat > "$TD/mock-rpc-aborted.sh" <<'M'
#!/usr/bin/env bash
echo '{"type":"ready"}'
while IFS= read -r _l; do
  printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"aborted"}]}}' '{"type":"turn_end","message":{"stopReason":"aborted"}}'
done
M
chmod +x "$TD/mock-rpc-aborted.sh"
echo "$GP" | jq '.channel="rpc"' | bash "$S/omp-start.sh" --package-json - --task-id rpcabort >/dev/null 2>&1
OMP_BIN="$TD/mock-rpc-aborted.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-rpcabort.json" --max-time 30 >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rpcabort.json" >/dev/null 2>&1; chk "rpc aborted 立即拒绝→2" 2 $?
chk "  rpc aborted rejected" rejected "$(jq -r .status "$TD/omp-state-rpcabort.json")"
bash "$S/omp-finish.sh" --state "$TD/omp-state-rpcabort.json" --human-review >/dev/null 2>&1

echo "═══ 11. RPC→Shell 降级（rpc daemon 不就绪）═══"
cat > "$TD/mock-degrade.sh" <<'M'
#!/usr/bin/env bash
case "$*" in
  *"--mode rpc"*) exit 1 ;;  # rpc 立即退 → daemon 不就绪 → 触发降级
  *) printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"nit\",\"summary\":\"shell fallback\",\"evidence\":[{\"type\":\"file\",\"ref\":\"y:1\"}]}\n```"}]}}' '{"type":"turn_end","message":{"role":"assistant","stopReason":"stop","content":[{"type":"text","text":"x"}]}}' ;;
esac
M
chmod +x "$TD/mock-degrade.sh"
echo "$GP" | jq '.channel="rpc"' | bash "$S/omp-start.sh" --package-json - --task-id rpc2 >/dev/null 2>&1
OMP_BIN="$TD/mock-degrade.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-rpc2.json" --max-time 10 >/dev/null 2>&1
chk "rpc 失败降级 shell" shell "$(jq -r '.run.channel_used' "$TD/omp-state-rpc2.json")"
chk "降级标记 degraded_from=rpc" rpc "$(jq -r '.run.degraded_from' "$TD/omp-state-rpc2.json")"

echo "═══ 12. ACP 通道（delegate_task → pending_acp）═══"
echo "$GP" | jq '.channel="acp"' | bash "$S/omp-start.sh" --package-json - --task-id acp1 >/dev/null 2>&1
OMP_BIN="$TD/mock-rpc.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-acp1.json" >/dev/null 2>&1; chk "acp send→0（pending_acp）" 0 $?
chk "acp status=pending_acp" pending_acp "$(jq -r '.status' "$TD/omp-state-acp1.json")"
chk "acp channel_used=acp" acp "$(jq -r '.run.channel_used' "$TD/omp-state-acp1.json")"
# ════ 13. --watch 模式（v0.5.0 STDD 修复）══════════════════════════
echo "═══ 13. --watch 模式 ═══"

# Setup mock state (ACP channel, so --watch should reject)
cat > "$TD/omp-test-state.json" << STATEEOF
{"task_id":"test-watch","status":"running","run":{"channel_used":"acp","raw_output":"$TD/omp-raw-test-watch.json","max_time":300}}
STATEEOF

# 13a: ACP 拒绝 --watch
echo -n "  🧪 watch-acp-reject ... "
OUT=$(bash "$S/omp-monitor.sh" --state "$TD/omp-test-state.json" --watch 2>&1) || true
if echo "$OUT" | grep -q "不支持 ACP"; then echo "✅"; else echo "❌ 未检测到 ACP 拒绝 (got: ${OUT:0:80})"; ((F++)); fi

# 13b: --interval 非法值
echo -n "  🧪 watch-bad-interval ... "
bash "$S/omp-monitor.sh" --state "$TD/omp-test-state.json" --watch --interval abc 2>/dev/null; RC=$?
[[ $RC -eq 3 ]] && echo "✅" || { echo "❌ exit=$RC 期望 3"; ((F++)); }

# 13c: --help 覆盖 --watch
echo -n "  🧪 watch-help ... "
OUT=$(bash "$S/omp-monitor.sh" --help 2>&1)
if echo "$OUT" | grep -q "\-\-watch"; then echo "✅"; else echo "❌"; ((F++)); fi

((P+=3))

# ════ 14. 稳健判决提取（多 fenced / 多裸对象 / text_delta / 空证据红线）══════════
echo "═══ 14. 稳健判决提取 ═══"

# 14a mock：prose + 两个 fenced 块，前 blocker（陈旧草稿）后 pass（终稿）→ 应选末个 pass
cat > "$TD/mock-multifence.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"初审草稿\n```json\n{\"severity\":\"blocker\",\"summary\":\"旧稿误报\",\"evidence\":[{\"ref\":\"a:1\"}]}\n```\n复核后终稿：\n```json\n{\"severity\":\"pass\",\"summary\":\"复核通过\",\"evidence\":[{\"ref\":\"b:2\"}]}\n```"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
# 14b mock：自由文本里多个裸对象，末个才是合法判决 → 应选末个 concern
cat > "$TD/mock-baremulti.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"元数据 {\"note\":\"ignore\"} 前置草稿 {\"severity\":\"blocker\",\"summary\":\"stale\",\"evidence\":[{\"ref\":\"a\"}]} 最终结论 {\"severity\":\"concern\",\"summary\":\"最终裁决\",\"evidence\":[{\"ref\":\"b\"}]}"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
# 14c mock：仅 text_delta 流（无 message_end 汇总块）→ 按序拼接还原后提取
cat > "$TD/mock-delta.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' \
'{"type":"session","id":"d1"}' \
'{"type":"assistantMessageEvent","assistantMessageEvent":{"type":"text_delta","delta":"delta prefix "}}' \
'{"type":"assistantMessageEvent","assistantMessageEvent":{"type":"text_delta","delta":"{\"severity\":\"pass\","}}' \
'{"type":"assistantMessageEvent","assistantMessageEvent":{"type":"text_delta","delta":"\"summary\":\"delta 拼接终稿\",\"evidence\":[{\"ref\":\"z:1\"}]}"}}' \
'{"type":"turn_end","message":{"stopReason":"stop"}}'
M
# 14d mock：两 fenced，前 blocker（有证据）后 pass（空证据）→ 选末个 pass，但空证据仍触发 exit 10
cat > "$TD/mock-lastempty.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"草稿\n```json\n{\"severity\":\"blocker\",\"summary\":\"有证据草稿\",\"evidence\":[{\"ref\":\"a:1\"}]}\n```\n终稿\n```json\n{\"severity\":\"pass\",\"summary\":\"空证据终稿\",\"evidence\":[]}\n```"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
chmod +x "$TD"/mock-multifence.sh "$TD"/mock-baremulti.sh "$TD"/mock-delta.sh "$TD"/mock-lastempty.sh

# 14a: gate-verify 直判 + monitor 端到端都应选末个 pass（非首个 blocker）
"$TD/mock-multifence.sh" > "$TD/raw-mf.json"
GVMF=$(bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-mf.json" 2>/dev/null); chk "多fenced gate→0" 0 $?
echo "$GVMF" | grep -q 'severity=pass' && chk "  多fenced gate 选 pass" y y || chk "  多fenced gate 选 pass" y n
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id mf1 >/dev/null 2>&1
OMP_BIN="$TD/mock-multifence.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-mf1.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-mf1.json" >/dev/null 2>&1; chk "多fenced monitor→reported" 0 $?
chk "  monitor 选末个 severity=pass" pass "$(jq -r .monitor.severity "$TD/omp-state-mf1.json")"

# 14b: 多裸对象 → 选末个合法判决 concern
"$TD/mock-baremulti.sh" > "$TD/raw-bm.json"
GVBM=$(bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-bm.json" 2>/dev/null); chk "多裸对象 gate→0" 0 $?
echo "$GVBM" | grep -q 'severity=concern' && chk "  多裸对象选末个 concern" y y || chk "  多裸对象选末个 concern" y n

# 14c: text_delta-only → 拼接还原后提取成功
"$TD/mock-delta.sh" > "$TD/raw-dl.json"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-dl.json" >/dev/null 2>&1; chk "text_delta gate→0" 0 $?
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id dl1 >/dev/null 2>&1
OMP_BIN="$TD/mock-delta.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-dl1.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-dl1.json" >/dev/null 2>&1; chk "text_delta monitor→reported" 0 $?
chk "  text_delta severity=pass" pass "$(jq -r .monitor.severity "$TD/omp-state-dl1.json")"

# 14d: 末个合法判决为空证据 → 仍触发 evidence 硬红线 exit 10 / rejected（选末不绕过红线）
"$TD/mock-lastempty.sh" > "$TD/raw-le.json"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-le.json" >/dev/null 2>&1; chk "末个空证据 gate→10" 10 $?
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id le1 >/dev/null 2>&1
OMP_BIN="$TD/mock-lastempty.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-le1.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-le1.json" >/dev/null 2>&1; chk "末个空证据 monitor→10" 10 $?
chk "  状态 rejected" rejected "$(jq -r .status "$TD/omp-state-le1.json")"

# ════ 15. 证据包生成器 + 输入契约收窄 + execute 端到端 ══════════════
echo "═══ 15. 证据包 + 契约收窄 + execute 端到端 ═══"

# 15a: bundle --help → 0
bash "$S/omp-bundle-code-audit.sh" --help >/dev/null 2>&1; chk "bundle --help→0" 0 $?

# 15b: bundle 生成形状 + 敏感路径排除（非 git 目录，验证 tolerate 非 git）
SRC="$TD/bundle-src"; mkdir -p "$SRC/lib" "$SRC/config"
printf 'console.log(1)\n' > "$SRC/app.js"
printf 'export const x=1\n' > "$SRC/lib/util.js"
printf 'API_KEY=xxx\n'   > "$SRC/.env"
printf 'shhh\n'          > "$SRC/config/secret-config.txt"
printf 'PRIVATE\n'       > "$SRC/api.key"
BND="$TD/bundle-out"
bash "$S/omp-bundle-code-audit.sh" --repo "$SRC" --out "$BND" >/dev/null 2>&1; chk "bundle 生成→0" 0 $?
_shape=y
for art in manifest.json summary.md file-list.txt git-status.txt diff.patch; do
  [[ -f "$BND/$art" ]] || _shape=n
done
chk "  bundle 5 产物齐全" y "$_shape"
jq -e 'type=="object" and .kind=="omp-code-audit-evidence-bundle"' "$BND/manifest.json" >/dev/null 2>&1 && chk "  manifest 合法 JSON" y y || chk "  manifest 合法 JSON" y n
grep -q '^app.js$' "$BND/file-list.txt" 2>/dev/null && chk "  普通文件入包" y y || chk "  普通文件入包" y n
if grep -Eq '(^|/)(\.env|api\.key|config/secret-config\.txt)$' "$BND/file-list.txt" 2>/dev/null; then chk "  敏感路径已排除" y n; else chk "  敏感路径已排除" y y; fi
chk "  manifest sensitive_excluded=3" 3 "$(jq -r '.sensitive_excluded' "$BND/manifest.json" 2>/dev/null)"
chk "  manifest is_git=false" false "$(jq -r '.is_git' "$BND/manifest.json" 2>/dev/null)"
BND_ABS="$TD/bundle-out-abs"
bash "$S/omp-bundle-code-audit.sh" --repo "$SRC" --out "$BND_ABS" --scope "$SRC/lib" >/dev/null 2>&1; chk "bundle 绝对 scope→0" 0 $?
grep -q '^lib/util.js$' "$BND_ABS/file-list.txt" 2>/dev/null && chk "  绝对 scope 归一为相对路径" y y || chk "  绝对 scope 归一为相对路径" y n
# 15b-2: git diff 默认不含 untracked；bundle 必须把未跟踪新文件正文追加到 diff.patch，供 bundle_only 审计
GIT_SRC="$TD/bundle-git-src"; mkdir -p "$GIT_SRC/scripts"
( cd "$GIT_SRC" && git init -q && git config user.email test.invalid && git config user.name test && printf 'base\n' > README.md && git add README.md && git commit -qm init )
printf '#!/usr/bin/env bash\necho new-file-body\n' > "$GIT_SRC/scripts/new-tool.sh"
printf 'SECRET=bad\n' > "$GIT_SRC/scripts/token.key"
BND_GIT="$TD/bundle-git-out"
bash "$S/omp-bundle-code-audit.sh" --repo "$GIT_SRC" --out "$BND_GIT" --scope scripts >/dev/null 2>&1; chk "bundle git untracked→0" 0 $?
grep -q '^scripts/new-tool.sh$' "$BND_GIT/file-list.txt" 2>/dev/null && chk "  untracked 普通文件入 file-list" y y || chk "  untracked 普通文件入 file-list" y n
grep -q 'new-file-body' "$BND_GIT/diff.patch" 2>/dev/null && chk "  untracked 正文入 diff.patch" y y || chk "  untracked 正文入 diff.patch" y n
if grep -q 'SECRET=bad' "$BND_GIT/diff.patch" 2>/dev/null; then chk "  untracked 敏感正文不入 diff" y n; else chk "  untracked 敏感正文不入 diff" y y; fi

# 15c: gate-verify package 契约收窄
mkpkg '.task_id="t"|.channel="ftp"' > "$TD/pkg-badch.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-badch.json" >/dev/null 2>&1; chk "非法 channel→1" 1 $?
mkpkg '.task_id="t"|.mode="destroy"' > "$TD/pkg-badmode.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-badmode.json" >/dev/null 2>&1; chk "非法 mode→1" 1 $?
mkpkg '.task_id="t"|.mode="govern:clean"' > "$TD/pkg-gov.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-gov.json" >/dev/null 2>&1; chk "govern:clean mode→0" 0 $?
mkpkg '.task_id="t"|.mode="execute"|.criterion=[]' > "$TD/pkg-exe.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-exe.json" >/dev/null 2>&1; chk "execute 空 criterion 豁免→0" 0 $?
mkpkg '.task_id="t"|.auditor.independence_level="bundle_only"' > "$TD/pkg-bo-no.json"
GVBO=$(bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-bo-no.json" 2>/dev/null); chk "bundle_only 缺 path→1" 1 $?
echo "$GVBO" | grep -q 'evidence_bundle.path' && chk "  缺失字段含 evidence_bundle.path" y y || chk "  缺失字段含 evidence_bundle.path" y n
mkpkg '.task_id="t"|.auditor.independence_level="bundle_only"|.evidence_bundle={path:"'"$BND/manifest.json"'"}' > "$TD/pkg-bo-ok.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-bo-ok.json" >/dev/null 2>&1; chk "bundle_only 带 path→0" 0 $?
mkpkg '.task_id="t"|.auditor.independence_level="wild"' > "$TD/pkg-il.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-il.json" >/dev/null 2>&1; chk "非法 independence_level→1" 1 $?

# 15c-2: --allow-write 全面隔离，不开放任何写模式
mkpkg '.task_id="aw-audit"' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
bash "$S/omp-send.sh" --state "$TD/omp-state-aw-audit.json" --allow-write --dry-run >/dev/null 2>&1; chk "audit --allow-write→2" 2 $?
[[ ! -e "$TD/omp-counter-aw-audit.json" ]] && chk "  --allow-write 拒绝不消耗 round" y y || chk "  --allow-write 拒绝不消耗 round" y n
mkpkg '.task_id="aw-clean"|.mode="govern:clean"|.scope.cwd="/tmp/repo"|.risk={level:"high",dangerous_modes:[],rollback:"restore backup"}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
bash "$S/omp-send.sh" --state "$TD/omp-state-aw-clean.json" --allow-write --dry-run >/dev/null 2>&1; chk "govern:clean --allow-write 隔离→2" 2 $?

# 15c-3: execute capability_grant v1（显式能力；旧 package 仍保持只读）
CAP_WORK="$TD/cap-work"; CAP_EXTRA="$CAP_WORK/extra"; mkdir -p "$CAP_EXTRA"
CAP_GRANT=$(jq -cn --arg cwd "$CAP_WORK" --arg extra "$CAP_EXTRA" '{contract:"call-omp.capability-grant.v1",tools:["read","write","edit","bash"],approval:"non_interactive",cwd:$cwd,add_dirs:[$extra]}')
mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" '.task_id="cap-audit"|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' > "$TD/pkg-cap-audit.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-cap-audit.json" >/dev/null 2>&1; chk "audit capability grant→1" 1 $?
mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" '.task_id="cap-unknown"|.mode="execute"|.criterion=[]|.capability_grant=($cap|.tools=["read","warp_drive"])|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' > "$TD/pkg-cap-unknown.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-cap-unknown.json" >/dev/null 2>&1; chk "未知 capability tool→1" 1 $?
mkpkg --arg cwd "$CAP_WORK" '.task_id="cap-null"|.mode="execute"|.criterion=[]|.capability_grant=null|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' > "$TD/pkg-cap-null.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-cap-null.json" >/dev/null 2>&1; chk "显式 null capability grant→1" 1 $?
# 结构负例：版本/审批/字段/重复项/缺 cwd/不支持通道均 fail-closed
for spec in \
  'cap-badcontract|.capability_grant.contract="call-omp.capability-grant.v9"' \
  'cap-badapproval|.capability_grant.approval="interactive"' \
  'cap-unknownfield|.capability_grant.extra=true' \
  'cap-duptool|.capability_grant.tools=["read","read"]' \
  'cap-dupdir|.capability_grant.add_dirs=[$cwd,$cwd]' \
  'cap-nocwd|.capability_grant.cwd=""'; do
  id=${spec%%|*}; filter=${spec#*|}
  mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" ".task_id=\"$id\"|.mode=\"execute\"|.criterion=[]|.capability_grant=\$cap|.scope={allowed_paths:[\$cwd],denied_paths:[],cwd:\$cwd}|$filter" > "$TD/pkg-$id.json"
  bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-$id.json" >/dev/null 2>&1; chk "$id 结构拒绝→1" 1 $?
done
for ch in rpc acp; do
  mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" --arg ch "$ch" '.task_id=("cap-channel-"+$ch)|.channel=$ch|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' > "$TD/pkg-cap-channel-$ch.json"
  bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-cap-channel-$ch.json" >/dev/null 2>&1; chk "capability channel=$ch 拒绝→1" 1 $?
done
mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" --arg bnd "$BND/manifest.json" '.task_id="cap-bundle"|.mode="execute"|.criterion=[]|.auditor.independence_level="bundle_only"|.evidence_bundle.path=$bnd|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' > "$TD/pkg-cap-bundle.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-cap-bundle.json" >/dev/null 2>&1; chk "bundle_only + capability 拒绝→1" 1 $?

# launch 负例：只读 grant 的 cwd/add_dirs 也必须被 scope 覆盖；路径必须真实
CAP_OUT="$TD/cap-out"; mkdir -p "$CAP_OUT"
CAP_RO=$(jq -cn --arg cwd "$CAP_WORK" --arg out "$CAP_OUT" '{contract:"call-omp.capability-grant.v1",tools:["read"],approval:"non_interactive",cwd:$cwd,add_dirs:[$out]}')
CAP_READ_NOCWD=$(printf '%s' "$CAP_RO" | jq '.cwd=""|.add_dirs=[]')
mkpkg --argjson cap "$CAP_READ_NOCWD" --arg cwd "$CAP_WORK" '.task_id="cap-read-nocwd"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[]}' > "$TD/pkg-cap-read-nocwd.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-cap-read-nocwd.json" >/dev/null 2>&1; chk "只读 grant 缺 cwd→1" 1 $?
CAP_READ_DENIED=$(printf '%s' "$CAP_RO" | jq --arg cwd "$CAP_WORK" '.cwd=$cwd|.add_dirs=[]')
mkpkg --argjson cap "$CAP_READ_DENIED" --arg cwd "$CAP_WORK" '.task_id="cap-read-denied"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[($cwd+"/secret")],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-read-denied.json" >/dev/null 2>&1; chk "只读 grant + denied_paths→2" 2 $?
mkpkg --argjson cap "$CAP_READ_DENIED" --arg cwd "$CAP_WORK" '.task_id="cap-scope-cwd-type"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:false}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-scope-cwd-type.json" >/dev/null 2>&1; chk "scope.cwd 非字符串→2" 2 $?
mkpkg --argjson cap "$CAP_RO" --arg cwd "$CAP_WORK" '.task_id="cap-ro-out"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-ro-out.json" >/dev/null 2>&1; chk "只读 grant add_dir 越 scope→2" 2 $?
CAP_REL=$(printf '%s' "$CAP_GRANT" | jq '.cwd="relative"|.add_dirs=[]')
mkpkg --argjson cap "$CAP_REL" --arg cwd "$CAP_WORK" '.task_id="cap-relative"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[]}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-relative.json" >/dev/null 2>&1; chk "capability 相对 cwd→2" 2 $?
CAP_MISSING=$(printf '%s' "$CAP_GRANT" | jq --arg p "$TD/does-not-exist" '.cwd=$p|.add_dirs=[]')
mkpkg --argjson cap "$CAP_MISSING" --arg cwd "$CAP_WORK" '.task_id="cap-missing"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[]}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-missing.json" >/dev/null 2>&1; chk "capability 不存在 cwd→2" 2 $?

mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" '.task_id="cap-denied"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:["/tmp/no"],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-denied.json" >/dev/null 2>&1; chk "mutable grant + denied_paths 启动前拒绝→2" 2 $?

cat > "$TD/mock-capability.sh" <<'M'
#!/usr/bin/env bash
: "${CAPTURE_ARGS:?}"
printf '%s\n' "$@" > "$CAPTURE_ARGS"
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"STATUS: completed"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
chmod +x "$TD/mock-capability.sh"
mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" '.task_id="cap-exec"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1; chk "execute capability start→0" 0 $?
CAPTURE_ARGS="$TD/cap-args.txt" OMP_BIN="$TD/mock-capability.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-exec.json" >/dev/null 2>&1; chk "execute capability send→0" 0 $?
python3 - "$TD/cap-args.txt" "$CAP_WORK" "$CAP_EXTRA" <<'PY'
import os,sys
args=open(sys.argv[1],encoding='utf-8').read().splitlines()
def has_pair(a,b): return any(args[i:i+2]==[a,b] for i in range(len(args)-1))
assert has_pair('--tools','read,write,edit,bash')
assert has_pair('--approval-mode','yolo')
assert '--auto-approve' not in args
assert has_pair('--cwd',os.path.realpath(sys.argv[2]))
assert has_pair('--add-dir',os.path.realpath(sys.argv[3]))
PY
chk "  grant 精确映射 tools/approval/cwd/add-dir" 0 $?
chk "  state 记录 capability contract" call-omp.capability-grant.v1 "$(jq -r '.run.capability.contract' "$TD/omp-state-cap-exec.json")"
chk "  state 记录 launch fingerprint" 64 "$(jq -r '.run.launch_fingerprint|length' "$TD/omp-state-cap-exec.json")"
CAP_PROMPT="$TD/omp-prompt-cap-exec.txt"
grep -q '不套审计 verdict schema' "$CAP_PROMPT" 2>/dev/null && chk "  execute prompt 不再强制审计 JSON" y y || chk "  execute prompt 不再强制审计 JSON" y n
chk "  grant launch 不叠加 legacy auto-approve" false "$(jq -r '.run.launch_spec.auto_approve' "$TD/omp-state-cap-exec.json")"
chk "  launch spec 绑定 OMP binary hash" 64 "$(jq -r '.run.launch_spec.omp_bin_sha256|length' "$TD/omp-state-cap-exec.json")"
chk "  launch spec 绑定 system prompt hash" 64 "$(jq -r '.run.launch_spec.system_hash|length' "$TD/omp-state-cap-exec.json")"
chk "  launch spec 绑定 resolved capability fingerprint" y "$(jq -r 'if .run.launch_spec.capability_fingerprint == .run.capability.fingerprint then "y" else "n" end' "$TD/omp-state-cap-exec.json")"
CAP_BIN_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$TD/mock-capability.sh")
chk "  launch spec 绑定 canonical OMP binary path" "$CAP_BIN_REAL" "$(jq -r '.run.launch_spec.omp_bin_path' "$TD/omp-state-cap-exec.json")"

# CLI override 与审批冲突必须在 launch 前拒绝
for ov in rpc acp; do
  id="cap-override-$ov"
  mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" --arg id "$id" '.task_id=$id|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
  OMP_BIN="$TD/mock-capability.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-$id.json" --channel "$ov" --dry-run >/dev/null 2>&1; chk "grant --channel $ov override→2" 2 $?
done
mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" '.task_id="cap-noapprove"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
OMP_BIN="$TD/mock-capability.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-noapprove.json" --no-auto-approve --dry-run >/dev/null 2>&1; chk "grant --no-auto-approve 冲突→2" 2 $?

# symlink 经 realpath 后应与 scope parity，并把规范路径传给 OMP
ln -s "$CAP_WORK" "$TD/cap-link"
CAP_LINK=$(printf '%s' "$CAP_GRANT" | jq --arg p "$TD/cap-link" '.cwd=$p|.add_dirs=[]')
mkpkg --argjson cap "$CAP_LINK" --arg cwd "$CAP_WORK" '.task_id="cap-symlink"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
CAPTURE_ARGS="$TD/cap-symlink-args.txt" OMP_BIN="$TD/mock-capability.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-symlink.json" >/dev/null 2>&1; chk "grant symlink canonical parity→0" 0 $?
chk "  canonical cwd 写入 state" "$(cd "$CAP_WORK" && pwd -P)" "$(jq -r '.run.capability.cwd' "$TD/omp-state-cap-symlink.json")"

# 同一参数、不同 OMP binary 内容必须产生不同启动指纹
cp "$TD/mock-capability.sh" "$TD/mock-capability-v2.sh"; printf '\n# v2 identity\n' >> "$TD/mock-capability-v2.sh"; chmod +x "$TD/mock-capability-v2.sh"
mkpkg --argjson cap "$CAP_GRANT" --arg cwd "$CAP_WORK" '.task_id="cap-bin2"|.mode="execute"|.criterion=[]|.capability_grant=$cap|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
CAPTURE_ARGS="$TD/cap-bin2-args.txt" OMP_BIN="$TD/mock-capability-v2.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-bin2.json" >/dev/null 2>&1
FP1=$(jq -r '.run.launch_fingerprint' "$TD/omp-state-cap-exec.json"); FP2=$(jq -r '.run.launch_fingerprint' "$TD/omp-state-cap-bin2.json")
[[ "$FP1" != "$FP2" ]] && chk "  OMP binary 变化→启动指纹变化" y y || chk "  OMP binary 变化→启动指纹变化" y n

mkpkg --arg cwd "$CAP_WORK" '.task_id="cap-legacy"|.mode="execute"|.criterion=[]|.scope={allowed_paths:[$cwd],denied_paths:[],cwd:$cwd}' | bash "$S/omp-start.sh" --package-json - >/dev/null 2>&1
CAPTURE_ARGS="$TD/cap-legacy-args.txt" OMP_BIN="$TD/mock-capability.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cap-legacy.json" >/dev/null 2>&1
LEGACY_TOOLS=$(python3 - "$TD/cap-legacy-args.txt" <<'PY'
import sys
args=open(sys.argv[1],encoding='utf-8').read().splitlines()
print(args[args.index('--tools')+1])
PY
)
chk "  旧 execute 仍是只读默认" read,grep,glob,lsp,web_search "$LEGACY_TOOLS"
grep -qx -- '--auto-approve' "$TD/cap-legacy-args.txt" && chk "  legacy 仍保留 auto-approve" y y || chk "  legacy 仍保留 auto-approve" y n

# 15d: execute 模式端到端（空证据允许——execute 豁免证据红线）
cat > "$TD/mock-exec.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' \
'{"type":"session","id":"e1"}' \
'{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"STATUS: completed\nSUMMARY: 跑通 build\nFILES: app.js"}]}}' \
'{"type":"turn_end","message":{"role":"assistant","stopReason":"stop","content":[{"type":"text","text":"done"}]}}'
M
chmod +x "$TD/mock-exec.sh"
echo "$GP" | jq '.mode="execute"|.criterion=[]' | bash "$S/omp-start.sh" --package-json - --task-id ex1 >/dev/null 2>&1; chk "execute start→gated" 0 $?
chk "  状态 gated" gated "$(jq -r .status "$TD/omp-state-ex1.json")"
OMP_BIN="$TD/mock-exec.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-ex1.json" >/dev/null 2>&1; chk "execute send→0" 0 $?
bash "$S/omp-monitor.sh" --state "$TD/omp-state-ex1.json" >/dev/null 2>&1; chk "execute monitor→reported" 0 $?
chk "  状态 reported" reported "$(jq -r .status "$TD/omp-state-ex1.json")"
# 长自由文本不得因 `producer | head` + pipefail 触发 SIGPIPE/rc=141。
cat > "$TD/mock-exec-long.sh" <<'M'
#!/usr/bin/env bash
python3 - <<'PY'
import json
print(json.dumps({"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"长输出"*40000}]}},ensure_ascii=False))
print(json.dumps({"type":"turn_end","message":{"role":"assistant","stopReason":"stop"}},ensure_ascii=False))
PY
M
chmod +x "$TD/mock-exec-long.sh"
echo "$GP" | jq '.mode="execute"|.criterion=[]' | bash "$S/omp-start.sh" --package-json - --task-id exlong >/dev/null 2>&1
OMP_BIN="$TD/mock-exec-long.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-exlong.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-exlong.json" >/dev/null 2>&1; chk "execute 长输出 monitor 不因 SIGPIPE 中断" 0 $?
chk "  execute 长输出状态 reported" reported "$(jq -r .status "$TD/omp-state-exlong.json")"
chk "  execute 摘要截为 160 字符" 160 "$(jq -r '.monitor.summary|length' "$TD/omp-state-exlong.json")"
jq '.run.exit_code=7' "$TD/omp-state-ex1.json" > "$TD/ex1-tmp.json" && mv "$TD/ex1-tmp.json" "$TD/omp-state-ex1.json"
bash "$S/omp-finish.sh" --state "$TD/omp-state-ex1.json" --accept >/dev/null 2>&1; chk "finish 防御：reported+exit7→2" 2 $?
jq '.run.exit_code=0' "$TD/omp-state-ex1.json" > "$TD/ex1-tmp.json" && mv "$TD/ex1-tmp.json" "$TD/omp-state-ex1.json"
bash "$S/omp-finish.sh" --state "$TD/omp-state-ex1.json" --accept >/dev/null 2>&1; chk "execute accept 空证据→0" 0 $?
chk "  状态 accepted" accepted "$(jq -r .status "$TD/omp-state-ex1.json")"
printf 'keep\n' > "$TD/victim.err"; printf 'keep\n' > "$TD/victim.exit"
jq --arg raw "$TD/victim" '.status="reported"|.run.raw_output=$raw' "$TD/omp-state-ex1.json" > "$TD/omp-state-spoof.json"
bash "$S/omp-finish.sh" --state "$TD/omp-state-spoof.json" --accept >/dev/null 2>&1; chk "finish 拒绝非规范 raw 路径→3" 3 $?
[[ -f "$TD/victim.err" && -f "$TD/victim.exit" ]] && chk "  spoof 路径未删除" y y || chk "  spoof 路径未删除" y n

# 15e: 非终态 stopReason 与 execute 非零退出必须 fail-closed
cat > "$TD/mock-tooluse.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"{\"severity\":\"pass\",\"summary\":\"partial\",\"evidence\":[{\"type\":\"reference\",\"ref\":\"x:1\"}]}"}]}}' '{"type":"turn_end","message":{"stopReason":"toolUse"}}'
M
cat > "$TD/mock-exec-fail.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"execution failed"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
exit 7
M
chmod +x "$TD/mock-tooluse.sh" "$TD/mock-exec-fail.sh"
"$TD/mock-tooluse.sh" > "$TD/raw-tooluse.json"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-tooluse.json" >/dev/null 2>&1; chk "toolUse 非终态 gate→1" 1 $?
echo "$GP" | jq '.mode="execute"|.criterion=[]' | bash "$S/omp-start.sh" --package-json - --task-id exfail >/dev/null 2>&1
OMP_BIN="$TD/mock-exec-fail.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-exfail.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-exfail.json" >/dev/null 2>&1; chk "execute exit7 monitor→2" 2 $?
chk "  execute exit7 rejected" rejected "$(jq -r .status "$TD/omp-state-exfail.json")"
bash "$S/omp-finish.sh" --state "$TD/omp-state-exfail.json" --accept >/dev/null 2>&1; chk "execute exit7 accept→2" 2 $?

cat > "$TD/mock-exec-async-fail.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"async failed"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
exit 7
M
chmod +x "$TD/mock-exec-async-fail.sh"
echo "$GP" | jq '.mode="execute"|.criterion=[]' | bash "$S/omp-start.sh" --package-json - --task-id exasyncfail >/dev/null 2>&1
OMP_BIN="$TD/mock-exec-async-fail.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-exasyncfail.json" --async >/dev/null 2>&1
APID=$(jq -r '.run.pid' "$TD/omp-state-exasyncfail.json")
for _ in $(seq 1 50); do kill -0 "$APID" 2>/dev/null || break; sleep 0.1; done
bash "$S/omp-monitor.sh" --state "$TD/omp-state-exasyncfail.json" >/dev/null 2>&1; chk "async execute exit7 monitor→2" 2 $?
chk "  async exit code 已持久化" 7 "$(jq -r '.run.exit_code' "$TD/omp-state-exasyncfail.json")"
chk "  async execute exit7 rejected" rejected "$(jq -r '.status' "$TD/omp-state-exasyncfail.json")"

# ════ 16. Package C：紧凑诊断 compact_debug（拒绝路径落 .monitor.compact_debug，不回吐 raw）══
echo "═══ 16. 紧凑诊断 compact_debug ═══"

# 16a mock：turn_end 有但无任何 JSON verdict（纯散文）→ no_candidate 拒绝 + compact_debug
cat > "$TD/mock-noverdict.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"我看了一圈代码，感觉没什么大问题，应该可以。"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
# 16b mock：JSON verdict 但 severity 非法值 → severity 拒绝 + compact_debug
cat > "$TD/mock-badsev.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"critical\",\"summary\":\"越权\",\"evidence\":[{\"ref\":\"a:1\"}]}\n```"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
# 16c mock：assistant 最终文本为空（有 turn_end，但 text 为空串）→ 拒绝 + compact_debug
cat > "$TD/mock-emptytext.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":""}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
chmod +x "$TD"/mock-noverdict.sh "$TD"/mock-badsev.sh "$TD"/mock-emptytext.sh

# 16a: 无 JSON verdict → rejected + compact_debug.failure_stage=no_candidate
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id cd1 >/dev/null 2>&1
OMP_BIN="$TD/mock-noverdict.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cd1.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-cd1.json" >/dev/null 2>&1
chk "无verdict→rejected" rejected "$(jq -r .status "$TD/omp-state-cd1.json")"
chk "  compact_debug 已落且非 null" object "$(jq -r '.monitor.compact_debug|type' "$TD/omp-state-cd1.json")"
# 纯散文无任何 JSON verdict → 最早在 gate-verify 结构校验被拒（gate_reason 记录原因）
chk "  failure_stage=no_candidate" no_candidate "$(jq -r '.monitor.compact_debug.failure_stage' "$TD/omp-state-cd1.json")"
chk "  gate_reason 非空" y "$([[ -n "$(jq -r '.monitor.compact_debug.gate_reason' "$TD/omp-state-cd1.json")" ]] && echo y || echo n)"
chk "  raw_bytes 为数字" number "$(jq -r '.monitor.compact_debug.raw_bytes|type' "$TD/omp-state-cd1.json")"
chk "  candidate_count=0" 0 "$(jq -r '.monitor.compact_debug.candidate_count' "$TD/omp-state-cd1.json")"
chk "  last_candidate_parseable=false" false "$(jq -r '.monitor.compact_debug.last_candidate_parseable' "$TD/omp-state-cd1.json")"
# 未回吐 raw：compact_debug 尾部截断，整体远小于把 raw 全塞进去（散文 raw 很小，验证字段结构即可）
chk "  final_text_tail 为字符串" string "$(jq -r '.monitor.compact_debug.final_text_tail|type' "$TD/omp-state-cd1.json")"

# 16b: severity 非法 → rejected + failure_stage=severity + last_candidate_keys 记录键
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id cd2 >/dev/null 2>&1
OMP_BIN="$TD/mock-badsev.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cd2.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-cd2.json" >/dev/null 2>&1
chk "非法severity→rejected" rejected "$(jq -r .status "$TD/omp-state-cd2.json")"
chk "  failure_stage=severity" severity "$(jq -r '.monitor.compact_debug.failure_stage' "$TD/omp-state-cd2.json")"
chk "  last_candidate_parseable=true" true "$(jq -r '.monitor.compact_debug.last_candidate_parseable' "$TD/omp-state-cd2.json")"
jq -e '.monitor.compact_debug.last_candidate_keys|index("severity")' "$TD/omp-state-cd2.json" >/dev/null 2>&1 && chk "  last_candidate_keys 含 severity" y y || chk "  last_candidate_keys 含 severity" y n

# 16c: 空 assistant 最终文本 → rejected + compact_debug（final_text_bytes=0）
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id cd3 >/dev/null 2>&1
OMP_BIN="$TD/mock-emptytext.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-cd3.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-cd3.json" >/dev/null 2>&1
chk "空最终文本→rejected" rejected "$(jq -r .status "$TD/omp-state-cd3.json")"
chk "  compact_debug 已落" object "$(jq -r '.monitor.compact_debug|type' "$TD/omp-state-cd3.json")"
chk "  final_text_bytes=0" 0 "$(jq -r '.monitor.compact_debug.final_text_bytes' "$TD/omp-state-cd3.json")"
chk "  failure_stage=no_final_text" no_final_text "$(jq -r '.monitor.compact_debug.failure_stage' "$TD/omp-state-cd3.json")"

# 16d: --json 输出含 debug 信号且整体仍是合法 JSON
CDJSON=$(bash "$S/omp-monitor.sh" --state "$TD/omp-state-cd1.json" --json 2>/dev/null)
echo "$CDJSON" | jq -e . >/dev/null 2>&1 && chk "--json 仍合法 JSON" y y || chk "--json 仍合法 JSON" y n
chk "  --json compact_debug=true" true "$(echo "$CDJSON" | jq -r '.compact_debug')"

# 16e: execute 模式（reported）不落 compact_debug（仅拒绝且非 execute 才落）
CDEXE=$(bash "$S/omp-monitor.sh" --state "$TD/omp-state-ex1.json" --json 2>/dev/null)
chk "execute --json compact_debug=false" false "$(echo "$CDEXE" | jq -r '.compact_debug')"
chk "  execute state compact_debug=null" null "$(jq -r '.monitor.compact_debug' "$TD/omp-state-ex1.json")"

# 16f: 成功 reported（accept 场景 f1）不落 compact_debug
chk "reported 成功不落 compact_debug" null "$(jq -r '.monitor.compact_debug' "$TD/omp-state-f1.json")"

echo "═══ 17. 跨平台 mock-only 冒烟（call-omp-smoke.sh）═══"
SMOKE="$S/call-omp-smoke.sh"
# 17a: --help → 0（纯打印头注，无 agent 调用）
bash "$SMOKE" --help >/dev/null 2>&1; chk "smoke --help→0" 0 $?
# 17b/c: codex / claude-code 冒烟即便 OMP_BIN=/nonexistent 也过（本就不调 omp）→ 0
mkdir -p "$TD/smoke-codex" "$TD/smoke-cc"
OMP_BIN=/nonexistent bash "$SMOKE" --platform codex --out "$TD/smoke-codex" >"$TD/smoke-codex.out" 2>&1; chk "codex smoke(OMP_BIN=/nonexistent)→0" 0 $?
OMP_BIN=/nonexistent bash "$SMOKE" --platform claude-code --out "$TD/smoke-cc" >/dev/null 2>&1; chk "claude-code smoke(OMP_BIN=/nonexistent)→0" 0 $?
# 17d: omp-self 冒烟输出 recursion_guard=armed
OMP_BIN=/nonexistent bash "$SMOKE" --platform omp-self --out "$TD/smoke-self" >"$TD/smoke-self.out" 2>&1; chk "omp-self smoke→0" 0 $?
grep -q "recursion_guard=armed" "$TD/smoke-self.out" && chk "omp-self 输出 recursion_guard=armed" y y || chk "omp-self 输出 recursion_guard=armed" y n
# 17e: CALL_OMP_SELF_CALL_DEPTH=1 → 拒绝（退出码 4，非零），不跑嵌套
CALL_OMP_SELF_CALL_DEPTH=1 bash "$SMOKE" --platform omp-self --out "$TD/smoke-depth" >"$TD/smoke-depth.out" 2>&1; chk "DEPTH>=1 拒绝→4" 4 $?
grep -q "recursion_guard=tripped" "$TD/smoke-depth.out" && chk "DEPTH>=1 输出 recursion_guard=tripped" y y || chk "DEPTH>=1 输出 recursion_guard=tripped" y n
# 17f: 冒烟报告提及 gate 结果与 bundle 产物路径（manifest.json）
grep -qi "gate" "$TD/smoke-codex.out" && chk "冒烟报告含 gate" y y || chk "冒烟报告含 gate" y n
grep -q "manifest.json" "$TD/smoke-codex.out" && chk "冒烟报告含 bundle manifest 路径" y y || chk "冒烟报告含 bundle manifest 路径" y n
# 17g: 非法平台 → 参数错误 3
bash "$SMOKE" --platform bogus >/dev/null 2>&1; chk "非法 --platform→3" 3 $?
# 17h: 缺省 --out 时自动创建的输出目录应保留，stdout 中 manifest 路径退出后仍可读
bash "$SMOKE" --platform codex >"$TD/smoke-default-out.out" 2>&1; chk "缺省 --out smoke→0" 0 $?
DEF_MANIFEST=$(awk -F': ' '/bundle manifest:/ {print $2}' "$TD/smoke-default-out.out" | tail -1)
[[ -r "$DEF_MANIFEST" ]] && chk "缺省 --out manifest 退出后可读" y y || chk "缺省 --out manifest 退出后可读" y n

# best-effort 清理本测试自动创建的输出目录，产物可读性断言已完成
[[ -n "${DEF_MANIFEST:-}" ]] && rm -rf "$(dirname "$(dirname "$DEF_MANIFEST")")" 2>/dev/null || true

echo "═══ 18. 平台发现清单 + check 脚本（call-omp-check.sh）═══"
ROOT="$SKILL_DIR"
CODEX_MF="$ROOT/.codex-plugin/plugin.json"
CLAUDE_MF="$ROOT/.claude-plugin/plugin.json"
OMP_MF="$ROOT/.omp-plugin/plugin.json"
CHECK="$S/call-omp-check.sh"
# 18a: 三份清单存在
[[ -f "$CODEX_MF" ]] && chk "codex 清单存在" y y || chk "codex 清单存在" y n
[[ -f "$CLAUDE_MF" ]] && chk "claude-code 清单存在" y y || chk "claude-code 清单存在" y n
[[ -f "$OMP_MF" ]] && chk "omp-self 清单存在" y y || chk "omp-self 清单存在" y n
# 18b: 三份均为合法 JSON
jq -e . "$CODEX_MF" >/dev/null 2>&1 && chk "codex 清单合法 JSON" y y || chk "codex 清单合法 JSON" y n
jq -e . "$CLAUDE_MF" >/dev/null 2>&1 && chk "claude-code 清单合法 JSON" y y || chk "claude-code 清单合法 JSON" y n
jq -e . "$OMP_MF" >/dev/null 2>&1 && chk "omp-self 清单合法 JSON" y y || chk "omp-self 清单合法 JSON" y n
# 18c: platform 值正确
chk "  codex platform=codex" codex "$(jq -r .platform "$CODEX_MF")"
chk "  claude platform=claude-code" claude-code "$(jq -r .platform "$CLAUDE_MF")"
chk "  omp platform=omp-self" omp-self "$(jq -r .platform "$OMP_MF")"
# 18d: check 脚本退出 0（三份齐全时）
bash "$CHECK" >/dev/null 2>&1; chk "call-omp-check→0" 0 $?
# 18e: OMP 清单提及 recursion guard
grep -qi "recursion" "$OMP_MF" && chk "omp-self 清单含 recursion guard" y y || chk "omp-self 清单含 recursion guard" y n
# 18f: 三份清单均引用冒烟脚本路径
grep -q "scripts/call-omp-smoke.sh" "$CODEX_MF" && chk "codex 清单引用冒烟脚本" y y || chk "codex 清单引用冒烟脚本" y n
grep -q "scripts/call-omp-smoke.sh" "$CLAUDE_MF" && chk "claude-code 清单引用冒烟脚本" y y || chk "claude-code 清单引用冒烟脚本" y n
grep -q "scripts/call-omp-smoke.sh" "$OMP_MF" && chk "omp-self 清单引用冒烟脚本" y y || chk "omp-self 清单引用冒烟脚本" y n
# 18g: 缺一份 → check 非零（只操作隔离 fixture，不移动真实 manifest）
CHECK_FIX="$TD/check-fixture"
mkdir -p "$CHECK_FIX/scripts" "$CHECK_FIX/.codex-plugin" "$CHECK_FIX/.claude-plugin" "$CHECK_FIX/.omp-plugin"
cp "$CHECK" "$CHECK_FIX/scripts/call-omp-check.sh"
cp "$CODEX_MF" "$CHECK_FIX/.codex-plugin/plugin.json"
cp "$CLAUDE_MF" "$CHECK_FIX/.claude-plugin/plugin.json"
cp "$OMP_MF" "$CHECK_FIX/.omp-plugin/plugin.json"
cp "$ROOT/SKILL.md" "$CHECK_FIX/SKILL.md"
mkdir -p "$CHECK_FIX/references"
cp "$ROOT/references/INDEX.md" "$CHECK_FIX/references/INDEX.md"
# INDEX 里的目标也复制，确保基线失败不会被其他缺件伪造
cp -R "$ROOT/references/." "$CHECK_FIX/references/"
cp "$ROOT/CHANGELOG.md" "$CHECK_FIX/CHANGELOG.md"
bash "$CHECK_FIX/scripts/call-omp-check.sh" >/dev/null 2>&1; chk "隔离 check fixture 基线→0" 0 $?
rm -f "$CHECK_FIX/.codex-plugin/plugin.json"
bash "$CHECK_FIX/scripts/call-omp-check.sh" >/dev/null 2>&1; MISS_RC=$?
chk "缺清单→check 非零" nonzero "$([[ $MISS_RC -ne 0 ]] && echo nonzero || echo zero)"

echo "═══ 19. OD-OMP-1 ACP smoke probe ═══"
ACP_SMOKE="$S/omp-acp-smoke.sh"
# 19a: --help 契约
bash "$ACP_SMOKE" --help >/dev/null 2>&1; chk "omp-acp-smoke --help" 0 $?
# 19b: mock-pass 路径（退出 0 + status=compatible_smoke_passed）
MOCK_PASS_OUT="$TD/acp-mock-pass"
bash "$ACP_SMOKE" --mock-pass --out "$MOCK_PASS_OUT" >/dev/null 2>&1; chk "mock-pass→0" 0 $?
chk "  status=compatible_smoke_passed" compatible_smoke_passed "$(jq -r .status "$MOCK_PASS_OUT/summary.json" 2>/dev/null)"
# 19c: mock-incompatible 路径（退出 2 + status=started_but_protocol_incompatible）
MOCK_INC_OUT="$TD/acp-mock-inc"
bash "$ACP_SMOKE" --mock-incompatible --out "$MOCK_INC_OUT" >/dev/null 2>&1; chk "mock-incompatible→2" 2 $?
chk "  status=started_but_protocol_incompatible" started_but_protocol_incompatible "$(jq -r .status "$MOCK_INC_OUT/summary.json" 2>/dev/null)"
# 19d: mock-timeout 路径（退出 3 + status=failed_to_start_or_timeout）
MOCK_TO_OUT="$TD/acp-mock-to"
bash "$ACP_SMOKE" --mock-timeout --out "$MOCK_TO_OUT" >/dev/null 2>&1; chk "mock-timeout→3" 3 $?
chk "  status=failed_to_start_or_timeout" failed_to_start_or_timeout "$(jq -r .status "$MOCK_TO_OUT/summary.json" 2>/dev/null)"
# 19e: 证据文件齐全（7 个）
for f in summary.json result.md stdin.ndjson stdout.ndjson stderr.log timeline.ndjson process.json; do
  [[ -f "$MOCK_PASS_OUT/$f" ]] && chk "  证据 $f 存在" y y || chk "  证据 $f 存在" y n
done
# 19f: mock 模式在 summary.json 标记
grep -q '"mock"' "$MOCK_PASS_OUT/summary.json" && chk "mock 标记" y y || chk "mock 标记" y n
# 19g: mock summary schema 与真实 schema 对齐
chk "  mock initialize_ok=true" true "$(jq -r .initialize_ok "$MOCK_PASS_OUT/summary.json" 2>/dev/null)"
chk "  mock session_observed=true" true "$(jq -r .session_observed "$MOCK_PASS_OUT/summary.json" 2>/dev/null)"
chk "  mock prompt_or_update_observed=true" true "$(jq -r .prompt_or_update_observed "$MOCK_PASS_OUT/summary.json" 2>/dev/null)"
# 19h: stdin 必须是 ACP JSON-RPC 形态，禁止退回 task_id/goal 自定义 prompt
grep -q '"method":"initialize"' "$MOCK_PASS_OUT/stdin.ndjson" && chk "  stdin 含 initialize" y y || chk "  stdin 含 initialize" y n

echo "═══ 20. OD-OMP-2 ACP interactive probe（零 token + hot-path 守护）═══"
ACP_PROBE="$S/omp-acp-probe.sh"
# 20a: --help 契约
bash "$ACP_PROBE" --help >/dev/null 2>&1; chk "omp-acp-probe --help" 0 $?

# 20b: mock-omp1632（退出 0 + dialect_detected + session/list）
MOCK_1632_OUT="$TD/probe-mock-1632"
bash "$ACP_PROBE" --mock-omp1632 --out "$MOCK_1632_OUT" >/dev/null 2>&1; chk "mock-omp1632→0" 0 $?
chk "  status=dialect_detected" dialect_detected "$(jq -r .status "$MOCK_1632_OUT/summary.json" 2>/dev/null)"
chk "  dialect=omp-session-capabilities" omp-session-capabilities "$(jq -r .dialect "$MOCK_1632_OUT/summary.json" 2>/dev/null)"
jq -e '.session_capabilities | index("list") and index("resume") and index("fork") and index("close")' "$MOCK_1632_OUT/summary.json" >/dev/null 2>&1 && chk "  capabilities 含 list/resume/fork/close" y y || chk "  capabilities 含 list/resume/fork/close" y n
jq -e '.probe_methods_sent | index("session/list")' "$MOCK_1632_OUT/summary.json" >/dev/null 2>&1 && chk "  sent_methods 含 session/list" y y || chk "  sent_methods 含 session/list" y n

# 20c: mock-session-new（退出 0 + standard dialect）
MOCK_SN_OUT="$TD/probe-mock-sn"
bash "$ACP_PROBE" --mock-session-new --out "$MOCK_SN_OUT" >/dev/null 2>&1; chk "mock-session-new→0" 0 $?
chk "  dialect=standard-session-new-prompt" standard-session-new-prompt "$(jq -r .dialect "$MOCK_SN_OUT/summary.json" 2>/dev/null)"
chk "  session_prompt_ok=true" true "$(jq -r .session_prompt_ok "$MOCK_SN_OUT/summary.json" 2>/dev/null)"

# 20d: mock-initialize-only（退出 2 + initialize_ok=true, capabilities=false）
MOCK_INIT_OUT="$TD/probe-mock-init"
bash "$ACP_PROBE" --mock-initialize-only --out "$MOCK_INIT_OUT" >/dev/null 2>&1; chk "mock-initialize-only→2" 2 $?
chk "  status=initialize_only" initialize_only "$(jq -r .status "$MOCK_INIT_OUT/summary.json" 2>/dev/null)"
chk "  initialize_ok=true" true "$(jq -r .initialize_ok "$MOCK_INIT_OUT/summary.json" 2>/dev/null)"
chk "  capabilities_observed=false" false "$(jq -r .capabilities_observed "$MOCK_INIT_OUT/summary.json" 2>/dev/null)"

# 20e: mock-timeout（退出 3 + status=failed_to_start_or_timeout）
MOCK_TO_PROBE_OUT="$TD/probe-mock-to"
bash "$ACP_PROBE" --mock-timeout --out "$MOCK_TO_PROBE_OUT" >/dev/null 2>&1; chk "mock-timeout→3" 3 $?
chk "  status=failed_to_start_or_timeout" failed_to_start_or_timeout "$(jq -r .status "$MOCK_TO_PROBE_OUT/summary.json" 2>/dev/null)"

# 20f: 证据文件齐全（7 个）
_probe_ev=y
for f in summary.json result.md stdin.ndjson stdout.ndjson stderr.log timeline.ndjson process.json; do
  [[ -f "$MOCK_1632_OUT/$f" ]] || _probe_ev=n
done
chk "  probe 7 证据文件齐全" y "$_probe_ev"

# 20g: probe_methods_sent schema（JSON 数组，包含方言探测方法）
SENT_METHODS=$(jq -r '.probe_methods_sent' "$MOCK_1632_OUT/summary.json" 2>/dev/null)
echo "$SENT_METHODS" | jq -e '. | type == "array"' >/dev/null 2>&1 && chk "  probe_methods_sent 是数组" y y || chk "  probe_methods_sent 是数组" y n
METHODS_COUNT=$(echo "$SENT_METHODS" | jq -r '. | length' 2>/dev/null)
chk "  probe_methods_sent 至少 3 个方法" y "$([[ "$METHODS_COUNT" -ge 3 ]] && echo y || echo n)"
echo "$SENT_METHODS" | jq -e '. | index("initialize")' >/dev/null 2>&1 && chk "  probe_methods_sent 含 initialize" y y || chk "  probe_methods_sent 含 initialize" y n
echo "$SENT_METHODS" | jq -e '. | index("session/list")' >/dev/null 2>&1 && chk "  probe_methods_sent 含 session/list" y y || chk "  probe_methods_sent 含 session/list" y n

# 20h: hot-path 守护（omp-start.sh / omp-send.sh 未被此 slice 修改）
HOT_START_AFTER=$(shasum "$S/omp-start.sh" 2>/dev/null | awk '{print $1}')
HOT_SEND_AFTER=$(shasum "$S/omp-send.sh" 2>/dev/null | awk '{print $1}')
chk "  omp-start.sh 测试前后 hash 一致" "$HOT_START_BEFORE" "$HOT_START_AFTER"
chk "  omp-send.sh 测试前后 hash 一致" "$HOT_SEND_BEFORE" "$HOT_SEND_AFTER"
[[ "$OMP_BIN" == "$TD/"* ]] && chk "  全局 OMP_BIN 指向隔离 mock" y y || chk "  全局 OMP_BIN 指向隔离 mock" y n

echo "═══ 21. bundle_only Shell → 资源监督 + 强制 async（P0B send slice）═══"
# 见证型 mock：被真正调用时向 witness.log 追加一行（用来证明 dry-run 不调、supervised 调）。
# 读 OMP_TMPDIR（supervisor 透传父进程 env），单引号 heredoc 内延迟到运行时展开。
cat > "$TD/mock-omp-witness.sh" <<'M'
#!/usr/bin/env bash
# P2A-static：无 --help 探测分支——thinking 完全由显式 OMP_BUNDLE_THINKING 决定。
echo invoked >> "${OMP_TMPDIR:-/tmp}/omp-witness.log"
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"concern\",\"summary\":\"bundle_only 审计\",\"evidence\":[{\"type\":\"file\",\"ref\":\"x:1\"}]}\n```"}]}}' '{"type":"turn_end","message":{"role":"assistant","stopReason":"stop"}}'
M
chmod +x "$TD/mock-omp-witness.sh"
echo '{}' > "$TD/bo-manifest.json"
BOP=$(echo "$GP" | jq '.auditor.independence_level="bundle_only" | .evidence_bundle={path:"'"$TD/bo-manifest.json"'"}')

# 21a: bundle_only shell send 不带 --async → 0，主状态含 async/supervised/watch + 规范资源路径，
#      且 OMP mock 经 supervisor 实际调用
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id bo1 >/dev/null 2>&1; chk "bundle_only start→gated" gated "$(jq -r .status "$TD/omp-state-bo1.json")"
rm -f "$TD/omp-witness.log"
OMP_BIN="$TD/mock-omp-witness.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-bo1.json" >/dev/null 2>&1; chk "bundle_only send(无--async)→0" 0 $?
BOST="$TD/omp-state-bo1.json"
chk "  run.mode=async（强制）" async "$(jq -r '.run.mode' "$BOST")"
chk "  run.resource_supervised=true" true "$(jq -r '.run.resource_supervised' "$BOST")"
chk "  run.watch_required=true" true "$(jq -r '.run.watch_required' "$BOST")"
chk "  run.channel_used=shell" shell "$(jq -r '.run.channel_used' "$BOST")"
chk "  run.resource_state 规范路径" "$TD/omp-resource-bo1.json" "$(jq -r '.run.resource_state' "$BOST")"
chk "  run.pid_store 规范路径" "$TD/omp-pids-bo1.json" "$(jq -r '.run.pid_store' "$BOST")"
chk "  run.pid 为数字（wrapper pid）" number "$(jq -r '.run.pid|type' "$BOST")"
# 等 supervisor wrapper 落 .exit sidecar（记 supervisor 退出码）
for _ in $(seq 1 80); do [[ -f "$TD/omp-raw-bo1.json.exit" ]] && break; sleep 0.1; done
chk "  .exit sidecar=supervisor 退出码 0" 0 "$(cat "$TD/omp-raw-bo1.json.exit" 2>/dev/null)"
chk "  资源 state schema=v1" call-omp-resource-supervisor.v1 "$(jq -r '.schema' "$TD/omp-resource-bo1.json" 2>/dev/null)"
chk "  资源 state status=reported" reported "$(jq -r '.status' "$TD/omp-resource-bo1.json" 2>/dev/null)"
[[ -f "$TD/omp-witness.log" ]] && chk "  OMP mock 实际被调用" y y || chk "  OMP mock 实际被调用" y n
jq -e '.argv[0]|endswith("mock-omp-witness.sh")' "$TD/omp-pids-bo1.json" >/dev/null 2>&1 && chk "  mock 经 supervisor argv 记录（穿过监督器）" y y || chk "  mock 经 supervisor argv 记录（穿过监督器）" y n
# 21d（零真实调用）：supervisor 只会 exec 隔离 mock，argv[0] 落在隔离目录内
jq -e --arg td "$TD" '.argv[0]|startswith($td)' "$TD/omp-pids-bo1.json" >/dev/null 2>&1 && chk "  supervisor 仅调隔离 mock（零真实 OMP/token/网络）" y y || chk "  supervisor 仅调隔离 mock（零真实 OMP/token/网络）" y n

# 21b: 常规（非 bundle_only）shell send 保持同步语义
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id bosync >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-bosync.json" >/dev/null 2>&1; chk "非 bundle_only shell send→0" 0 $?
chk "  普通 shell 仍同步 mode=sync" sync "$(jq -r '.run.mode' "$TD/omp-state-bosync.json")"
chk "  普通 shell 无 resource_supervised" null "$(jq -r '.run.resource_supervised' "$TD/omp-state-bosync.json")"

# 21c: bundle_only dry-run → 状态仍 gated、无 mock 调用、无资源副作用，且准确描述 async/supervisor
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id bodry >/dev/null 2>&1
rm -f "$TD/omp-witness.log"
DRYOUT=$(OMP_BIN="$TD/mock-omp-witness.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-bodry.json" --dry-run 2>/dev/null); chk "bundle_only dry-run→0" 0 $?
chk "  dry-run 仍 gated" gated "$(jq -r .status "$TD/omp-state-bodry.json")"
[[ ! -f "$TD/omp-witness.log" ]] && chk "  dry-run 未调用任何 mock" y y || chk "  dry-run 未调用任何 mock" y n
[[ ! -f "$TD/omp-resource-bodry.json" && ! -f "$TD/omp-pids-bodry.json" ]] && chk "  dry-run 无资源副作用" y y || chk "  dry-run 无资源副作用" y n
echo "$DRYOUT" | grep -q "supervisor" && chk "  dry-run 描述 supervisor 模式" y y || chk "  dry-run 描述 supervisor 模式" y n
echo "$DRYOUT" | grep -q "强制 --async" && chk "  dry-run 描述强制 async" y y || chk "  dry-run 描述强制 async" y n

# 21e: bundle_only 起始于 rpc，RPC 失败降级 Shell → 仍必须经 supervisor + 强制 async（P0B2R 修复）
# mock：--mode rpc 立即退（daemon 不就绪触发降级）；shell 模式落 witness 并给合法审计。
cat > "$TD/mock-bo-degrade.sh" <<'M'
#!/usr/bin/env bash
case "$*" in
  *"--mode rpc"*) exit 1 ;;
  *) echo invoked >> "${OMP_TMPDIR:-/tmp}/omp-bo-degrade-witness.log"
     printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"nit\",\"summary\":\"bundle_only rpc 降级 shell\",\"evidence\":[{\"type\":\"file\",\"ref\":\"y:1\"}]}\n```"}]}}' '{"type":"turn_end","message":{"role":"assistant","stopReason":"stop"}}' ;;
esac
M
chmod +x "$TD/mock-bo-degrade.sh"
BOP_RPC=$(echo "$BOP" | jq '.channel="rpc"')
echo "$BOP_RPC" | OMP_BIN="$TD/mock-bo-degrade.sh" bash "$S/omp-start.sh" --package-json - --task-id bofb >/dev/null 2>&1
chk "bundle_only 起始 channel=rpc" rpc "$(jq -r .channel "$TD/omp-state-bofb.json")"
rm -f "$TD/omp-bo-degrade-witness.log"
OMP_BIN="$TD/mock-bo-degrade.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-bofb.json" --max-time 10 >/dev/null 2>&1; chk "bundle_only rpc→shell 降级 send→0" 0 $?
FBST="$TD/omp-state-bofb.json"
chk "  降级 channel_used=shell" shell "$(jq -r '.run.channel_used' "$FBST")"
chk "  降级 degraded_from=rpc" rpc "$(jq -r '.run.degraded_from' "$FBST")"
chk "  降级 mode=async（强制，未逃逸同步）" async "$(jq -r '.run.mode' "$FBST")"
chk "  降级 resource_supervised=true" true "$(jq -r '.run.resource_supervised' "$FBST")"
chk "  降级 watch_required=true" true "$(jq -r '.run.watch_required' "$FBST")"
chk "  降级 resource_state 规范路径" "$TD/omp-resource-bofb.json" "$(jq -r '.run.resource_state' "$FBST")"
chk "  降级 pid_store 规范路径" "$TD/omp-pids-bofb.json" "$(jq -r '.run.pid_store' "$FBST")"
for _ in $(seq 1 80); do [[ -f "$TD/omp-raw-bofb.json.exit" ]] && break; sleep 0.1; done
chk "  降级 .exit=supervisor 退出码 0" 0 "$(cat "$TD/omp-raw-bofb.json.exit" 2>/dev/null)"
chk "  降级 资源 state status=reported" reported "$(jq -r '.status' "$TD/omp-resource-bofb.json" 2>/dev/null)"
[[ -f "$TD/omp-bo-degrade-witness.log" ]] && chk "  降级 mock 经 shell 实际调用" y y || chk "  降级 mock 经 shell 实际调用" y n
jq -e '.argv[0]|endswith("mock-bo-degrade.sh")' "$TD/omp-pids-bofb.json" >/dev/null 2>&1 && chk "  降级仅经 supervisor argv 调用（穿过监督器）" y y || chk "  降级仅经 supervisor argv 调用（穿过监督器）" y n
jq -e '.argv|index("-p") and index("json")' "$TD/omp-pids-bofb.json" >/dev/null 2>&1 && chk "  降级 argv 为 shell 模式（-p --mode json）" y y || chk "  降级 argv 为 shell 模式（-p --mode json）" y n
jq -e --arg td "$TD" '.argv[0]|startswith($td)' "$TD/omp-pids-bofb.json" >/dev/null 2>&1 && chk "  降级仅调隔离 mock（零真实 OMP/token/网络）" y y || chk "  降级仅调隔离 mock（零真实 OMP/token/网络）" y n
# 回归护栏：非 bundle_only 的 RPC 降级（§11 的 rpc2）保持同步 Shell，不被误监督
chk "  非 bundle_only rpc 降级仍同步 mode=sync" sync "$(jq -r '.run.mode' "$TD/omp-state-rpc2.json")"
chk "  非 bundle_only rpc 降级无 resource_supervised" null "$(jq -r '.run.resource_supervised' "$TD/omp-state-rpc2.json")"

echo "═══ 22. 资源监督拒绝 monitor 集成（P0B3）+ sidecar 认证（P0B3R）+ 最终契约认证/有界脱敏（P0B3R2）═══"
# 全程零真实 OMP/网络/token：直接构造主状态 + 监督器 forensic state（schema v1）+ pid sidecar，跑 monitor。
HEX64="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"  # 合法 64 位小写 hex digest
mk_sup_state() { # $1=task_id — 主 call-omp 状态：resource_supervised=true + 规范 sidecar 路径
  local id="$1"
  jq -n --arg id "$id" --arg raw "$TD/omp-raw-$id.json" \
        --arg rs "$TD/omp-resource-$id.json" --arg ps "$TD/omp-pids-$id.json" \
    '{task_id:$id,status:"running",package:{mode:"audit"},
      run:{channel_used:"shell",mode:"async",raw_output:$raw,
           resource_supervised:true,watch_required:true,
           resource_state:$rs,pid_store:$ps,pid:999999,round:1}}' > "$TD/omp-state-$id.json"
}
# 监督器 v1 forensic state：默认全字段合法（含 state_file/run.pid_store 规范绑定、raw_sha256 空、
# 非 starting 时 exit_code=0）；$3=可选 jq override（可引用 $hex=合法 64hex）。
mk_res() { local id="$1" st="$2" ov="${3:-.}"
  jq -n --arg id "$id" --arg raw "$TD/omp-raw-$id.json" --arg sf "$TD/omp-resource-$id.json" --arg ps "$TD/omp-pids-$id.json" --arg st "$st" \
    '{schema:"call-omp-resource-supervisor.v1",task_id:$id,task_id_source:"test",
      state_file:$sf,raw_output:$raw,raw_cap:2000000,
      raw_bytes:0,raw_lines:0,raw_sha256:"",raw_tail_bytes:0,
      rate_fuse:{enabled:false,window_bytes:0,window_seconds:1,fuse_windows:3,consecutive_over:0},
      status:$st,reason:"init",
      run:{started_at:"t",ended_at:"t",exit_code:(if $st=="starting" then null else 0 end),pid_store:$ps},
      child_identity:{pid:null,pgid:null,session_id:null,argv:[]}}' \
    | jq --arg hex "$HEX64" "$ov" > "$TD/omp-resource-$id.json"
}
# pid sidecar（监督器落盘格式）：pid/pgid/session_id 正整数 + argv 数组。
mk_pids() { jq -n --argjson pid "$2" --argjson pgid "$3" --argjson sid "$4" \
  '{pid:$pid,pgid:$pgid,session_id:$sid,argv:["omp","-p","--mode","json"],expected_pgid:null}' > "$1"; }

# 22a: resource_rejected（raw_cap）→ 主 rejected / exit 2 / 有界 forensic 保留 / 不拷 raw 正文 / 不留 argv
mk_sup_state rr1
mk_res rr1 resource_rejected '.reason="raw_cap_exceeded:2000001>2000000" | .raw_bytes=2000001 | .raw_lines=1234 | .raw_sha256=$hex | .raw_tail_bytes=4096 | .run.exit_code=137 | .child_identity={pid:4242,pgid:4242,session_id:4242,argv:["omp","-p","--append-system-prompt","ARGV_LEAK_CANARY"]}'
mk_pids "$TD/omp-pids-rr1.json" 4242 4242 4242
printf 'SECRET_RAW_LEAK_CANARY 这是绝不该被拷进 state 的 raw 正文\n' > "$TD/omp-raw-rr1.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rr1.json" >/dev/null 2>&1; chk "22a resource_rejected→exit 2" 2 $?
chk "  主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-rr1.json")"
chk "  run.exit_code=137" 137 "$(jq -r '.run.exit_code' "$TD/omp-state-rr1.json")"
chk "  monitor.resource.status=resource_rejected" resource_rejected "$(jq -r '.monitor.resource.status' "$TD/omp-state-rr1.json")"
chk "  monitor.resource.reason 保留" "raw_cap_exceeded:2000001>2000000" "$(jq -r '.monitor.resource.reason' "$TD/omp-state-rr1.json")"
chk "  monitor.resource.raw_bytes 保留" 2000001 "$(jq -r '.monitor.resource.raw_bytes' "$TD/omp-state-rr1.json")"
chk "  monitor.resource.raw_sha256 保留(64hex)" "$HEX64" "$(jq -r '.monitor.resource.raw_sha256' "$TD/omp-state-rr1.json")"
chk "  monitor.resource.child_identity.pid 保留" 4242 "$(jq -r '.monitor.resource.child_identity.pid' "$TD/omp-state-rr1.json")"
chk "  monitor.resource.child_identity 不含 argv（脱敏）" false "$(jq -r '.monitor.resource.child_identity|has("argv")' "$TD/omp-state-rr1.json")"
chk "  monitor.resource 不含顶层 argv" false "$(jq -r '.monitor.resource|has("argv")' "$TD/omp-state-rr1.json")"
chk "  未走判决解析（无 severity）" null "$(jq -r '.monitor.severity // "null"' "$TD/omp-state-rr1.json")"
grep -q SECRET_RAW_LEAK_CANARY "$TD/omp-state-rr1.json" && chk "  raw 正文未拷入 state" n y || chk "  raw 正文未拷入 state" n n
grep -q ARGV_LEAK_CANARY "$TD/omp-state-rr1.json" && chk "  argv canary 未拷入 state" n y || chk "  argv canary 未拷入 state" n n

# 22b: starting（pid sidecar 已就绪）→ phase running（不解析 raw、不改主状态）
mk_sup_state rs2
mk_res rs2 starting
mk_pids "$TD/omp-pids-rs2.json" 111 111 111
MJ=$(bash "$S/omp-monitor.sh" --state "$TD/omp-state-rs2.json" --json 2>/dev/null); RC=$?
chk "22b starting→exit 0" 0 $RC
chk "  phase=running" running "$(echo "$MJ" | jq -r .phase)"
chk "  主状态仍 running（未被改写）" running "$(jq -r .status "$TD/omp-state-rs2.json")"
chk "  未落 monitor.resource" null "$(jq -r '.monitor.resource // "null"' "$TD/omp-state-rs2.json")"

# 22c: 伪造/越权 sidecar 路径 或 非法/缺失 resource-state → rejected / exit 2（不跟随任意路径）
mk_sup_state rp3
jq '.run.resource_state="/tmp/evil-resource.json"' "$TD/omp-state-rp3.json" > "$TD/omp-state-rp3.json.t" && mv "$TD/omp-state-rp3.json.t" "$TD/omp-state-rp3.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rp3.json" >/dev/null 2>&1; chk "22c 伪造 resource_state 路径→exit 2" 2 $?
chk "  主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-rp3.json")"
mk_sup_state rp4
jq '.run.pid_store="/tmp/evil-pids.json"' "$TD/omp-state-rp4.json" > "$TD/omp-state-rp4.json.t" && mv "$TD/omp-state-rp4.json.t" "$TD/omp-state-rp4.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rp4.json" >/dev/null 2>&1; chk "22c 伪造 pid_store 路径→exit 2" 2 $?
chk "  主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-rp4.json")"
mk_sup_state rp5
printf 'not json {{{' > "$TD/omp-resource-rp5.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rp5.json" >/dev/null 2>&1; chk "22c 非法 resource-state JSON→exit 2" 2 $?
chk "  主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-rp5.json")"
mk_sup_state rp6  # 不创建 resource-state 文件（不可读）
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rp6.json" >/dev/null 2>&1; chk "22c 缺失 resource-state→exit 2" 2 $?
chk "  主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-rp6.json")"
mk_sup_state rp7; mk_res rp7 resource_rejected '.schema="totally-wrong.v9"'
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rp7.json" >/dev/null 2>&1; chk "22c schema 非法→exit 2" 2 $?

# 22c-sym: 文件系统安全（P0B3R2·A）—— resource-state / pid-store / raw 为 symlink → exit 2（不跟随）
printf 'x' > "$TD/symtarget.json"
mk_sup_state sym1; mk_res sym1 resource_rejected '.child_identity={pid:8,pgid:8,session_id:8,argv:[]} | .run.exit_code=1' ; mv "$TD/omp-resource-sym1.json" "$TD/sym1-real.json"; ln -s "$TD/sym1-real.json" "$TD/omp-resource-sym1.json"; mk_pids "$TD/omp-pids-sym1.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-sym1.json" >/dev/null 2>&1; chk "22c-sym resource-state symlink→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-sym1.json")" == *"symlink"* ]] && chk "  issue=symlink 拒绝跟随" y y || chk "  issue=symlink 拒绝跟随" y n
mk_sup_state sym2; mk_res sym2 resource_rejected '.child_identity={pid:8,pgid:8,session_id:8,argv:[]} | .run.exit_code=1'; ln -s "$TD/symtarget.json" "$TD/omp-pids-sym2.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-sym2.json" >/dev/null 2>&1; chk "22c-sym pid-store symlink→exit 2" 2 $?
mk_sup_state sym3; mk_res sym3 resource_rejected '.child_identity={pid:8,pgid:8,session_id:8,argv:[]} | .run.exit_code=1'; mk_pids "$TD/omp-pids-sym3.json" 8 8 8; ln -s "$TD/symtarget.json" "$TD/omp-raw-sym3.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-sym3.json" >/dev/null 2>&1; chk "22c-sym raw symlink→exit 2" 2 $?801|
# 22d: reported → 进入既有正常判决解析流（severity/evidence 照常产出）
mk_sup_state rd8
mk_res rd8 reported '.reason="normal_completion" | .raw_bytes=512 | .raw_lines=3 | .raw_sha256=$hex | .raw_tail_bytes=512 | .run.exit_code=0 | .child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-rd8.json" 5 5 5
"$TD/mock-omp.sh" > "$TD/omp-raw-rd8.json"; printf '0\n' > "$TD/omp-raw-rd8.json.exit"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rd8.json" >/dev/null 2>&1; chk "22d reported→既有解析→reported(0)" 0 $?
chk "  主状态 reported" reported "$(jq -r .status "$TD/omp-state-rd8.json")"
chk "  severity=concern（走了既有判决解析）" concern "$(jq -r '.monitor.severity' "$TD/omp-state-rd8.json")"
chk "  evidence=1（既有 gate-verify/抽取生效）" 1 "$(jq -r '.monitor.evidence_count' "$TD/omp-state-rd8.json")"

# 22e: containment_failure/child_not_reaped（界内）verbatim 保留，绝不软化
mk_sup_state rc9
mk_res rc9 resource_rejected '.reason="raw_cap_exceeded:9>8; containment_failure:child_not_reaped" | .raw_bytes=9 | .raw_lines=1 | .raw_sha256=$hex | .raw_tail_bytes=9 | .run.exit_code=124 | .child_identity={pid:7,pgid:7,session_id:7,argv:[]}'
mk_pids "$TD/omp-pids-rc9.json" 7 7 7
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rc9.json" >/dev/null 2>&1; chk "22e containment_failure→exit 2" 2 $?
chk "  resource.reason 保留 containment marker verbatim" "raw_cap_exceeded:9>8; containment_failure:child_not_reaped" "$(jq -r '.monitor.resource.reason' "$TD/omp-state-rc9.json")"
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-rc9.json")" == *"containment_failure:child_not_reaped"* ]] && chk "  issues 保留 containment marker" y y || chk "  issues 保留 containment marker" y n
chk "  run.exit_code=124" 124 "$(jq -r '.run.exit_code' "$TD/omp-state-rc9.json")"

# 22f: valid rejected（监督器 spawn 前硬错误：identity 全 null、exit_code null、无 pid-store）→ 主 rejected / exit 2（保留 reason）
mk_sup_state rh10
mk_res rh10 rejected '.reason="exec_failed:FileNotFoundError" | .run.exit_code=null | .rate_fuse=null'
bash "$S/omp-monitor.sh" --state "$TD/omp-state-rh10.json" >/dev/null 2>&1; chk "22f valid rejected（硬错误）→exit 2" 2 $?
chk "  主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-rh10.json")"
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-rh10.json")" == *"exec_failed:FileNotFoundError"* ]] && chk "  issues 保留监督器 reason（未软化）" y y || chk "  issues 保留监督器 reason（未软化）" y n

echo "─── P0B3R sidecar 内容认证 ───"
# 22h: 终态 pid-store 缺失 → exit 2（不 fail-open）
mk_sup_state ph11; mk_res ph11 resource_rejected '.reason="raw_cap_exceeded:5>4" | .raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=137 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'
bash "$S/omp-monitor.sh" --state "$TD/omp-state-ph11.json" >/dev/null 2>&1; chk "22h 终态 pid-store 缺失→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-ph11.json")" == *"pid sidecar 缺失"* ]] && chk "  issue=pid sidecar 缺失" y y || chk "  issue=pid sidecar 缺失" y n
# 22i: pid-store 非法 JSON → exit 2
mk_sup_state ph12; mk_res ph12 resource_rejected '.raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=137 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'
printf 'not json {{{' > "$TD/omp-pids-ph12.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-ph12.json" >/dev/null 2>&1; chk "22i pid-store 非法 JSON→exit 2" 2 $?
# 22j: pid-store 身份字段非法（缺 pid + argv 非数组）→ exit 2
mk_sup_state ph13; mk_res ph13 resource_rejected '.raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=137 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'
jq -n '{pgid:8,session_id:8,argv:"not-an-array"}' > "$TD/omp-pids-ph13.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-ph13.json" >/dev/null 2>&1; chk "22j pid-store 身份字段非法→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-ph13.json")" == *"身份字段非法"* ]] && chk "  issue=身份字段非法" y y || chk "  issue=身份字段非法" y n
# 22j-2: pid 非正整数（0）→ exit 2
mk_sup_state ph13b; mk_res ph13b resource_rejected '.raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'
mk_pids "$TD/omp-pids-ph13b.json" 0 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-ph13b.json" >/dev/null 2>&1; chk "22j-2 pid=0（非正整数）→exit 2" 2 $?
# 22k: pid-store 身份与 child_identity 不一致 → exit 2
mk_sup_state ph14; mk_res ph14 resource_rejected '.raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=137 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'
mk_pids "$TD/omp-pids-ph14.json" 9 9 9
bash "$S/omp-monitor.sh" --state "$TD/omp-state-ph14.json" >/dev/null 2>&1; chk "22k pid-store 身份错配→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-ph14.json")" == *"不一致"* ]] && chk "  issue=child_identity 不一致" y y || chk "  issue=child_identity 不一致" y n

echo "─── P0B3R2 契约绑定/形状 + 有界脱敏 ───"
# 22q: task_id / state_file / raw_output / run.pid_store 绑定不符 → 逐一 exit 2
mk_sup_state q1; mk_res q1 resource_rejected '.task_id="WRONG-ID" | .raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q1.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q1.json" >/dev/null 2>&1; chk "22q task_id 绑定不符→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-q1.json")" == *"task_id"* ]] && chk "  issue 提及 task_id" y y || chk "  issue 提及 task_id" y n
mk_sup_state q2; mk_res q2 resource_rejected '.state_file="/tmp/evil-state.json" | .raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q2.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q2.json" >/dev/null 2>&1; chk "22q state_file 绑定不符→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-q2.json")" == *"state_file"* ]] && chk "  issue 提及 state_file" y y || chk "  issue 提及 state_file" y n
mk_sup_state q3; mk_res q3 resource_rejected '.raw_output="/tmp/evil-raw.json" | .raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q3.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q3.json" >/dev/null 2>&1; chk "22q raw_output 绑定不符→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-q3.json")" == *"raw_output"* ]] && chk "  issue 提及 raw_output" y y || chk "  issue 提及 raw_output" y n
mk_sup_state q4; mk_res q4 resource_rejected '.run.pid_store="/tmp/evil-pids.json" | .raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q4.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q4.json" >/dev/null 2>&1; chk "22q run.pid_store 绑定不符→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-q4.json")" == *"pid_store"* ]] && chk "  issue 提及 run.pid_store" y y || chk "  issue 提及 run.pid_store" y n
# 22r: 未知 status / 错误必需类型 → exit 2
mk_sup_state q5; mk_res q5 bogus_status '.raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q5.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q5.json" >/dev/null 2>&1; chk "22r 未知 status→exit 2" 2 $?
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-q5.json")" == *"status_enum"* ]] && chk "  issue=status_enum" y y || chk "  issue=status_enum" y n
mk_sup_state q6; mk_res q6 resource_rejected '.raw_bytes="5" | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q6.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q6.json" >/dev/null 2>&1; chk "22r raw_bytes 类型错（string）→exit 2" 2 $?
mk_sup_state q7; mk_res q7 resource_rejected '.raw_sha256="deadbeefsha" | .raw_bytes=5 | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q7.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q7.json" >/dev/null 2>&1; chk "22r raw_sha256 非 64hex→exit 2" 2 $?
mk_sup_state q8; mk_res q8 resource_rejected '.reason=123 | .raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q8.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q8.json" >/dev/null 2>&1; chk "22r reason 非 string→exit 2" 2 $?
mk_sup_state q9; mk_res q9 reported '.reason="ok" | .raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=null | .child_identity={pid:8,pgid:8,session_id:8,argv:[]}'; mk_pids "$TD/omp-pids-q9.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q9.json" >/dev/null 2>&1; chk "22r 终态 exit_code=null→exit 2" 2 $?
mk_sup_state q10; mk_res q10 resource_rejected '.raw_bytes=5 | .raw_sha256=$hex | .run.exit_code=1 | .child_identity={pid:8,pgid:8,session_id:8,argv:"leak"}'; mk_pids "$TD/omp-pids-q10.json" 8 8 8
bash "$S/omp-monitor.sh" --state "$TD/omp-state-q10.json" >/dev/null 2>&1; chk "22r child_identity.argv 非数组→exit 2" 2 $?

# 22s: 启动窗口边界（P0B3R2·C）
mk_sup_state s1; mk_res s1 starting  # raw_bytes==0 + identity 全 null + pid-store 缺失 → running
MJ=$(bash "$S/omp-monitor.sh" --state "$TD/omp-state-s1.json" --json 2>/dev/null); RC=$?
chk "22s 有效启动窗口（缺 pid-store）→exit 0" 0 $RC; chk "  phase=running" running "$(echo "$MJ" | jq -r .phase)"
mk_sup_state s2; mk_res s2 starting '.raw_bytes=123'  # raw>0 + 缺 pid-store → fail-closed
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s2.json" >/dev/null 2>&1; chk "22s starting+raw>0+缺 pid-store→exit 2" 2 $?
mk_sup_state s3; mk_res s3 starting; printf 'not json {{{' > "$TD/omp-pids-s3.json"  # present-but-invalid → fail-closed
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s3.json" >/dev/null 2>&1; chk "22s starting+pid-store 非法→exit 2" 2 $?

# 22t: 有界脱敏（P0B3R2·D）—— argv prompt canary + 超长 reason（含末尾 containment）：
#      主状态既无 canary 也无 raw；reason/issue ≤512（+ 截断标记）；containment marker 仍在。
LONGR="raw_cap_exceeded:0>0 $(printf 'X%.0s' $(seq 1 680)) containment_failure:child_not_reaped"
mk_sup_state t1
jq -n --arg raw "$TD/omp-raw-t1.json" --arg sf "$TD/omp-resource-t1.json" --arg ps "$TD/omp-pids-t1.json" --arg hex "$HEX64" --arg reason "$LONGR" \
  '{schema:"call-omp-resource-supervisor.v1",task_id:"t1",task_id_source:"t",state_file:$sf,raw_output:$raw,raw_cap:2000000,
    raw_bytes:9,raw_lines:1,raw_sha256:$hex,raw_tail_bytes:9,rate_fuse:{enabled:false},status:"resource_rejected",reason:$reason,
    run:{started_at:"t",ended_at:"t",exit_code:137,pid_store:$ps},
    child_identity:{pid:8,pgid:8,session_id:8,argv:["omp","-p","--append-system-prompt","SYS_PROMPT_LEAK_CANARY","USER_MSG_LEAK_CANARY"]}}' > "$TD/omp-resource-t1.json"
mk_pids "$TD/omp-pids-t1.json" 8 8 8
printf 'RAW_BODY_LEAK_CANARY\n' > "$TD/omp-raw-t1.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-t1.json" >/dev/null 2>&1; chk "22t 超长 reason + argv canary → exit 2" 2 $?
grep -q LEAK_CANARY "$TD/omp-state-t1.json" && chk "  主状态无任何 LEAK_CANARY（argv/raw 未泄漏）" n y || chk "  主状态无任何 LEAK_CANARY（argv/raw 未泄漏）" n n
RLEN=$(jq -r '.monitor.resource.reason|length' "$TD/omp-state-t1.json"); [[ "$RLEN" -le 512 ]] && chk "  resource.reason ≤512（实测 ${RLEN}）" y y || chk "  resource.reason ≤512（实测 ${RLEN}）" y n
ILEN=$(jq -r '.monitor.issues[0]|length' "$TD/omp-state-t1.json"); [[ "$ILEN" -le 512 ]] && chk "  issue ≤512（实测 ${ILEN}）" y y || chk "  issue ≤512（实测 ${ILEN}）" y n
[[ "$(jq -r '.monitor.resource.reason' "$TD/omp-state-t1.json")" == *"containment_failure"* ]] && chk "  截断后仍保留 containment marker" y y || chk "  截断后仍保留 containment marker" y n
[[ "$(jq -r '.monitor.resource.reason' "$TD/omp-state-t1.json")" == *"truncated"* ]] && chk "  含确定性截断标记" y y || chk "  含确定性截断标记" y n
chk "  rate_fuse 仅标量子集(enabled)" false "$(jq -r '.monitor.resource.rate_fuse.enabled' "$TD/omp-state-t1.json")"

# 22u: 真实监督器产物贯通（§21 bo1 由真实 supervisor 写出 reported）→ 严格校验器接受真实输出并转既有解析
if [[ -f "$TD/omp-resource-bo1.json" && "$(jq -r '.status' "$TD/omp-resource-bo1.json" 2>/dev/null)" == "reported" ]]; then
  bash "$S/omp-monitor.sh" --state "$TD/omp-state-bo1.json" >/dev/null 2>&1; RC=$?
  chk "22u 真实 supervisor reported 贯通 monitor→reported(0)" 0 $RC
  chk "  主状态 reported" reported "$(jq -r .status "$TD/omp-state-bo1.json")"
  chk "  severity=concern（真实产物过严格校验+既有解析）" concern "$(jq -r '.monitor.severity' "$TD/omp-state-bo1.json")"
else
  chk "22u 真实 supervisor reported 贯通（前置 bo1 就绪）" y n
fi

# 22g: 非监督回归护栏 —— resource_supervised 缺失/false 完全跳过资源块（既有语义不变）
chk "  非监督 reported（§4 f1）无 monitor.resource" null "$(jq -r '.monitor.resource // "null"' "$TD/omp-state-f1.json")"

# ════ P1A. required_actions 单契约 + 加性输出闸 ══════════════════════
echo "═══ P1A. required_actions 契约 + 加性输出闸 ═══"
VAL="$S/required-actions-validate.py"
SCHEMA="$SKILL_DIR/contracts/required-actions.schema.json"

# 契约文件本身是合法 JSON + draft-2020-12 array 契约
jq -e 'type=="object" and .type=="array" and .items.properties.kind.enum' "$SCHEMA" >/dev/null 2>&1; chk "schema 合法 JSON + 派生根" 0 $?

# —— 直接校验：合法路径 ——
python3 "$VAL" --json '[{"kind":"revise","reason":"修 SQL"},{"kind":"human_review","reason":"需人裁"},{"kind":"stop","reason":"禁续跑"}]' >/dev/null 2>&1; chk "三种 kind 全合法→0" 0 $?
python3 "$VAL" --json '[{"kind":"revise","reason":"r","targets":["auth.ts:42","db.ts:8"]}]' >/dev/null 2>&1; chk "带 targets→0" 0 $?
python3 "$VAL" --json '[]' >/dev/null 2>&1; chk "空数组→0" 0 $?

# —— 直接校验：非法路径 ——
python3 "$VAL" --json '[{"kind":"bogus","reason":"r"}]' >/dev/null 2>&1; chk "非法 kind→1" 1 $?
python3 "$VAL" --json '[{"kind":"revise","reason":""}]' >/dev/null 2>&1; chk "空 reason→1" 1 $?
R513=$(printf 'x%.0s' $(seq 1 513)); jq -cn --arg r "$R513" '[{kind:"revise",reason:$r}]' > "$TD/ra-longreason.json"
python3 "$VAL" --file "$TD/ra-longreason.json" >/dev/null 2>&1; chk "超长 reason(513)→1" 1 $?
python3 "$VAL" --json '[{"kind":"revise","reason":"r","foo":1}]' >/dev/null 2>&1; chk "未知键→1" 1 $?
jq -cn '[range(9)|{kind:"revise",reason:("r"+(.|tostring))}]' > "$TD/ra-9.json"
python3 "$VAL" --file "$TD/ra-9.json" >/dev/null 2>&1; chk "9 个动作(>8)→1" 1 $?
python3 "$VAL" --json '[{"kind":"revise","reason":"r","targets":[""]}]' >/dev/null 2>&1; chk "空 target→1" 1 $?
python3 "$VAL" --json '[{"kind":"revise","reason":"r"},{"kind":"revise","reason":"r"}]' >/dev/null 2>&1; chk "重复动作对象→1" 1 $?
python3 "$VAL" --json '{"kind":"revise"}' >/dev/null 2>&1; chk "顶层非数组→1" 1 $?

# —— --file 路径 ——
echo '[{"kind":"stop","reason":"人工介入"}]' > "$TD/ra-file-ok.json"
python3 "$VAL" --file "$TD/ra-file-ok.json" >/dev/null 2>&1; chk "--file 合法→0" 0 $?

# —— 错误信封（P1A return 2）：任何用户/配置错误路径都产出单行 JSON、无 usage/traceback 泄漏 ——
# 缺参数：stdout 恒为可解析单行 JSON（ok=false, reason 非空），argparse usage 不得漏到 stdout
NOARG_OUT=$(python3 "$VAL" 2>/dev/null); chk "缺输入参数→3" 3 $?
echo "$NOARG_OUT" | jq -e 'type=="object" and .ok==false and (.reason|type=="string" and length>0)' >/dev/null 2>&1 \
  && chk "  缺参 stdout 单行 JSON(ok=false,reason 非空)" y y || chk "  缺参 stdout 单行 JSON(ok=false,reason 非空)" y n
echo "$NOARG_OUT" | grep -qi 'usage:' && chk "  缺参 stdout 无 usage 泄漏" n y || chk "  缺参 stdout 无 usage 泄漏" n n

# 畸形 --schema 覆盖（reason:null）：load_schema 必须拒收 → 单行 JSON + rc=3，绝不 AttributeError/traceback
echo '{"type":"array","items":{"type":"object","properties":{"kind":{"type":"string","enum":["revise"]},"reason":null}}}' > "$TD/ra-badschema.json"
BADSCH_OUT=$(python3 "$VAL" --json '[]' --schema "$TD/ra-badschema.json" 2>/dev/null); chk "畸形 override schema→3" 3 $?
echo "$BADSCH_OUT" | jq -e 'type=="object" and .ok==false and (.reason|length>0)' >/dev/null 2>&1 \
  && chk "  畸形 schema stdout 单行 JSON(无 traceback)" y y || chk "  畸形 schema stdout 单行 JSON(无 traceback)" y n
echo "$BADSCH_OUT" | grep -qi 'Traceback' && chk "  畸形 schema 无 traceback" n y || chk "  畸形 schema 无 traceback" n n

# —— gate 加性闸：构造带/不带 required_actions 的 mock raw JSONL ——
mk_ra_raw(){ # <outfile> <inner-compact-json>
  local out="$1" inner="$2" text
  text=$(printf '审计完成\n```json\n%s\n```' "$inner")
  jq -cn --arg t "$text" '{type:"message_end",message:{role:"assistant",content:[{type:"text",text:$t}]}}' > "$out"
  printf '%s\n' '{"type":"turn_end","message":{"stopReason":"stop"}}' >> "$out"
}

# legacy：无 required_actions → 保持既有行为（与 §1 raw-ok 同语义）
mk_ra_raw "$TD/ra-legacy.json" '{"severity":"concern","summary":"无该字段","evidence":[{"ref":"a:1"}]}'
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/ra-legacy.json" >/dev/null 2>&1; chk "legacy 无 required_actions→0" 0 $?

# 合法 required_actions（非 pass）→ 0
mk_ra_raw "$TD/ra-valid.json" '{"severity":"concern","summary":"有动作","evidence":[{"ref":"a:1"}],"required_actions":[{"kind":"revise","reason":"参数化","targets":["auth.ts:42"]}]}'
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/ra-valid.json" >/dev/null 2>&1; chk "合法 required_actions→0" 0 $?

# 畸形 required_actions（非法 kind）→ 1，且 stdout 必须是正常单行结构化 JSON 错误
# （set -e 下不得静默中断/泄漏 traceback；须保留 emit false 诊断形态）
mk_ra_raw "$TD/ra-bad.json" '{"severity":"concern","summary":"畸形动作","evidence":[{"ref":"a:1"}],"required_actions":[{"kind":"bogus","reason":"x"}]}'
GVRA=$(bash "$S/gate/gate-verify.sh" --mode output --file "$TD/ra-bad.json" 2>/dev/null); ra_rc=$?
chk "畸形 required_actions gate→1" 1 "$ra_rc"
echo "$GVRA" | jq -e 'type=="object"' >/dev/null 2>&1 && chk "  畸形 gate stdout 单行合法 JSON" y y || chk "  畸形 gate stdout 单行合法 JSON" y n
chk "  ok=false" false "$(echo "$GVRA" | jq -rc '.ok')"
RE=$(echo "$GVRA" | jq -rc '.reason // ""'); [[ -n "$RE" && ( "$RE" == *required_actions* || "$RE" == *契约* ) ]] && chk "  reason 非空且提及契约" y y || chk "  reason 非空且提及契约" y n
echo "$GVRA" | jq -e '(.missing_fields|type=="array") and (.missing_fields|index("required_actions"))' >/dev/null 2>&1 && chk "  missing_fields 含 required_actions" y y || chk "  missing_fields 含 required_actions" y n

# 未知键名含「字面换行」→ 校验器 reason 带换行流到 gate emit；emit 须安全 JSON 编码为单行
# （旧版 printf 只转义双引号，遇换行会产出两行/非法 JSON，违反单行 stdout 契约）
NLKEY_INNER=$(jq -cn '{severity:"concern",summary:"含换行未知键",evidence:[{ref:"a:1"}],required_actions:[{kind:"revise",reason:"x",("bad\nkey"):1}]}')
mk_ra_raw "$TD/ra-nlkey.json" "$NLKEY_INNER"
GVNL=$(bash "$S/gate/gate-verify.sh" --mode output --file "$TD/ra-nlkey.json" 2>/dev/null); nl_rc=$?
chk "换行未知键 gate→1" 1 "$nl_rc"
chk "  gate stdout 恰为单行" 1 "$(printf '%s\n' "$GVNL" | grep -c '')"
echo "$GVNL" | jq -e 'type=="object" and .ok==false and (.missing_fields|index("required_actions"))' >/dev/null 2>&1 \
  && chk "  换行 gate stdout jq 可解析(ok=false,含 required_actions)" y y || chk "  换行 gate stdout jq 可解析(ok=false,含 required_actions)" y n

# pass + 非空动作 → 1（pass 无 required action）
mk_ra_raw "$TD/ra-pass-ne.json" '{"severity":"pass","summary":"却带动作","evidence":[{"ref":"a:1"}],"required_actions":[{"kind":"revise","reason":"x"}]}'
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/ra-pass-ne.json" >/dev/null 2>&1; chk "pass+非空动作 gate→1" 1 $?

# pass + [] → 0
mk_ra_raw "$TD/ra-pass-empty.json" '{"severity":"pass","summary":"空动作","evidence":[{"ref":"a:1"}],"required_actions":[]}'
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/ra-pass-empty.json" >/dev/null 2>&1; chk "pass+[] gate→0" 0 $?

# next_action accept 回归守护（§4 已建 f1 归档，加性改动不得破坏）
grep -q 'next_action: accept' "$TD/omp-archive/f1/verdict.yaml" 2>/dev/null && chk "next_action accept 回归保持" y y || chk "next_action accept 回归保持" y n

# ════ P1B. template/monitor/finish 双写 required_actions（加性、向后兼容）═══════
echo "═══ P1B. 双写 required_actions（monitor 持久化 + finish YAML）═══"

# 从 verdict YAML 抠出 required_actions 的 flow-style JSON（= 合法 YAML 列表）
ra_from_yaml(){ grep '^required_actions: ' "$1" 2>/dev/null | head -1 | sed 's/^required_actions: //'; }

# 模板：schema 已含 required_actions 字段 + 硬约束条目
grep -q '"required_actions"' "$SKILL_DIR/templates/audit-prompt-template.md" && chk "模板 schema 含 required_actions 字段" y y || chk "模板 schema 含 required_actions 字段" y n
grep -q 'required_actions.*必填且与 severity 一致' "$SKILL_DIR/templates/audit-prompt-template.md" && chk "模板含 required_actions 硬约束" y y || chk "模板含 required_actions 硬约束" y n

# mock：内层 JSON 携带有序、合法的 required_actions（revise 在前、human_review 在后）
cat > "$TD/mock-p1b-valid.sh" <<'M'
#!/usr/bin/env bash
printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"concern\",\"summary\":\"有动作列表\",\"evidence\":[{\"type\":\"file\",\"ref\":\"auth.ts:42\"}],\"reject_instruction\":\"参数化\",\"required_actions\":[{\"kind\":\"revise\",\"reason\":\"参数化 SQL\",\"targets\":[\"auth.ts:42\"]},{\"kind\":\"human_review\",\"reason\":\"需人工确认删除\"}]}\n```"}]}}' '{"type":"turn_end","message":{"stopReason":"stop"}}'
M
chmod +x "$TD/mock-p1b-valid.sh"
EXP_RA='[{"kind":"revise","reason":"参数化 SQL","targets":["auth.ts:42"]},{"kind":"human_review","reason":"需人工确认删除"}]'

# —— B1：有效 required_actions → monitor 原样持久化（保序、legacy=false）——
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p1bv >/dev/null 2>&1
OMP_BIN="$TD/mock-p1b-valid.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p1bv.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-p1bv.json" >/dev/null 2>&1; chk "B1 有动作 monitor→reported" 0 $?
chk "  status reported" reported "$(jq -r .status "$TD/omp-state-p1bv.json")"
jq -e --argjson e "$EXP_RA" '.monitor.required_actions == $e' "$TD/omp-state-p1bv.json" >/dev/null 2>&1 && chk "  monitor.required_actions 精确保序" y y || chk "  monitor.required_actions 精确保序" y n
chk "  required_actions_legacy=false" false "$(jq -r '.monitor.required_actions_legacy' "$TD/omp-state-p1bv.json")"

# —— B2：普通 reject（未超限）→ 采用 monitor 的合法动作列表；legacy next_action 不受影响 ——
bash "$S/omp-finish.sh" --state "$TD/omp-state-p1bv.json" --reject >/dev/null 2>&1; chk "B2 finish reject→0" 0 $?
V="$TD/omp-verdict-p1bv.yaml"
grep -q 'next_action: revise' "$V" && chk "  legacy next_action: revise 保留" y y || chk "  legacy next_action: revise 保留" y n
ra_from_yaml "$V" | jq -e --argjson e "$EXP_RA" '. == $e' >/dev/null 2>&1 && chk "  YAML required_actions == monitor 规范列表" y y || chk "  YAML required_actions == monitor 规范列表" y n

# —— B3：legacy 无字段（mock-omp）→ monitor required_actions=null + legacy 标记，不发明动作 ——
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p1bl >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p1bl.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-p1bl.json" >/dev/null 2>&1; chk "B3 legacy monitor→reported" 0 $?
chk "  required_actions=null" null "$(jq -r '.monitor.required_actions' "$TD/omp-state-p1bl.json")"
chk "  required_actions_legacy=true" true "$(jq -r '.monitor.required_actions_legacy' "$TD/omp-state-p1bl.json")"
# §4 f1 同样是 legacy（无字段）→ 双写回归
chk "  §4 f1 legacy required_actions=null" null "$(jq -r '.monitor.required_actions' "$TD/omp-state-f1.json")"

# —— B4：legacy reject → 派生 revise（reason 非空、schema 合法）——
bash "$S/omp-finish.sh" --state "$TD/omp-state-p1bl.json" --reject >/dev/null 2>&1; chk "B4 legacy finish reject→0" 0 $?
VL="$TD/omp-verdict-p1bl.yaml"
ra_from_yaml "$VL" | jq -e 'length==1 and .[0].kind=="revise" and (.[0].reason|length>0)' >/dev/null 2>&1 && chk "  派生单条 revise + 非空 reason" y y || chk "  派生单条 revise + 非空 reason" y n
python3 "$VAL" --json "$(ra_from_yaml "$VL")" >/dev/null 2>&1; chk "  派生动作过 P1A 校验→0" 0 $?

# —— B5：human_review → 映射 human_review 动作 ——
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p1bh >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p1bh.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-p1bh.json" >/dev/null 2>&1
bash "$S/omp-finish.sh" --state "$TD/omp-state-p1bh.json" --human-review --reason "需产品确认" >/dev/null 2>&1; chk "B5 human-review finish→0" 0 $?
VH="$TD/omp-verdict-p1bh.yaml"
grep -q 'next_action: human_review' "$VH" && chk "  next_action: human_review 保留" y y || chk "  next_action: human_review 保留" y n
ra_from_yaml "$VH" | jq -e 'length==1 and .[0].kind=="human_review" and (.[0].reason|length>0)' >/dev/null 2>&1 && chk "  动作 kind=human_review + 非空 reason" y y || chk "  动作 kind=human_review + 非空 reason" y n

# —— B6：reject 计数超限 → next_action=stop 且动作映射 stop（exit 20）——
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p1bs >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p1bs.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-p1bs.json" >/dev/null 2>&1
bash "$S/gate/gate-counter.sh" --task-id p1bs --inc-reject >/dev/null 2>&1
bash "$S/gate/gate-counter.sh" --task-id p1bs --inc-reject >/dev/null 2>&1   # 已达 reject_limit=2
bash "$S/omp-finish.sh" --state "$TD/omp-state-p1bs.json" --reject >/dev/null 2>&1; chk "B6 超限 reject→20" 20 $?
VS="$TD/omp-verdict-p1bs.yaml"
grep -q 'next_action: stop' "$VS" && chk "  next_action: stop 保留" y y || chk "  next_action: stop 保留" y n
ra_from_yaml "$VS" | jq -e 'length==1 and .[0].kind=="stop" and (.[0].reason|length>0)' >/dev/null 2>&1 && chk "  动作 kind=stop + 非空 reason" y y || chk "  动作 kind=stop + 非空 reason" y n

# —— B7：畸形持久化动作绝不泄入 finish → 退回安全 revise，保 next_action/exit 语义 ——
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p1bm >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p1bm.json" >/dev/null 2>&1
bash "$S/omp-monitor.sh" --state "$TD/omp-state-p1bm.json" >/dev/null 2>&1
# 注入畸形（非法 kind + 泄漏金丝雀）到已持久化的 monitor.required_actions
jq '.monitor.required_actions=[{"kind":"bogus","reason":"CANARY_BOGUS_LEAK"}]' "$TD/omp-state-p1bm.json" > "$TD/omp-state-p1bm.tmp" && mv "$TD/omp-state-p1bm.tmp" "$TD/omp-state-p1bm.json"
bash "$S/omp-finish.sh" --state "$TD/omp-state-p1bm.json" --reject >/dev/null 2>&1; chk "B7 畸形数据 finish reject→0" 0 $?
VM="$TD/omp-verdict-p1bm.yaml"
grep -q CANARY_BOGUS_LEAK "$VM" && chk "  畸形动作不得泄入 verdict" n y || chk "  畸形动作不得泄入 verdict" n n
grep -q 'next_action: revise' "$VM" && chk "  next_action: revise 语义保持" y y || chk "  next_action: revise 语义保持" y n
ra_from_yaml "$VM" | jq -e 'length==1 and .[0].kind=="revise"' >/dev/null 2>&1 && chk "  退回安全 revise 动作" y y || chk "  退回安全 revise 动作" y n
python3 "$VAL" --json "$(ra_from_yaml "$VM")" >/dev/null 2>&1; chk "  安全退回动作过 P1A 校验→0" 0 $?

# —— B8：finish accept 归档 YAML 保留 next_action: accept + 合法空 required_actions ——
grep -q 'required_actions: \[\]' "$TD/omp-archive/f1/verdict.yaml" 2>/dev/null && chk "B8 accept 归档 required_actions: []" y y || chk "B8 accept 归档 required_actions: []" y n
ra_from_yaml "$TD/omp-archive/f1/verdict.yaml" | jq -e '. == []' >/dev/null 2>&1 && chk "  空数组可解析为 JSON/YAML []" y y || chk "  空数组可解析为 JSON/YAML []" y n

# —— B9：P0 资源拒绝路径不受影响（资源分支 MON 不引入 required_actions 字段）——
if [[ -f "$TD/omp-state-t1.json" ]]; then
  chk "B9 资源拒绝 monitor 无 required_actions 字段" absent "$(jq -r '.monitor.required_actions // "absent"' "$TD/omp-state-t1.json")"
else
  chk "B9 资源拒绝路径前置就绪" y n
fi

# ════ P1C1. v1 外层判决契约 marker + 严格 required_actions 闸（加性、不误伤 legacy）══
echo "═══ P1C1. v1 外层判决契约 marker + 严格闸 ═══"
V1M="call-omp.required_actions.v1"

# C1-1: legacy 无 marker、无 required_actions → 保持既有兼容（0）
mk_ra_raw "$TD/c1-legacy.json" '{"severity":"concern","summary":"legacy 无 marker","evidence":[{"ref":"a:1"}]}'
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-legacy.json" >/dev/null 2>&1; chk "C1 legacy 无 marker/无动作→0" 0 $?

# C1-2: v1 pass + [] → 0
mk_ra_raw "$TD/c1-pass.json" "$(jq -cn --arg m "$V1M" '{severity:"pass",summary:"v1 达标",evidence:[{ref:"a:1"}],required_actions_contract:$m,required_actions:[]}')"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-pass.json" >/dev/null 2>&1; chk "C1 v1 pass+[]→0" 0 $?

# C1-3: v1 concern + 合法动作 → 0
mk_ra_raw "$TD/c1-concern.json" "$(jq -cn --arg m "$V1M" '{severity:"concern",summary:"v1 有动作",evidence:[{ref:"a:1"}],required_actions_contract:$m,required_actions:[{kind:"revise",reason:"参数化"}]}')"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-concern.json" >/dev/null 2>&1; chk "C1 v1 concern+动作→0" 0 $?

# C1-4: v1 缺 required_actions → 1（v1 必填，区别于 legacy 缺=豁免）
mk_ra_raw "$TD/c1-noact.json" "$(jq -cn --arg m "$V1M" '{severity:"concern",summary:"v1 缺动作",evidence:[{ref:"a:1"}],required_actions_contract:$m}')"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-noact.json" >/dev/null 2>&1; chk "C1 v1 缺 required_actions→1" 1 $?

# C1-5: v1 非 pass + [] → 1
mk_ra_raw "$TD/c1-nonpass-empty.json" "$(jq -cn --arg m "$V1M" '{severity:"blocker",summary:"v1 非 pass 空动作",evidence:[{ref:"a:1"}],required_actions_contract:$m,required_actions:[]}')"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-nonpass-empty.json" >/dev/null 2>&1; chk "C1 v1 非pass+[]→1" 1 $?

# C1-6: v1 pass + 非空动作 → 1
mk_ra_raw "$TD/c1-pass-ne.json" "$(jq -cn --arg m "$V1M" '{severity:"pass",summary:"v1 pass 却带动作",evidence:[{ref:"a:1"}],required_actions_contract:$m,required_actions:[{kind:"revise",reason:"x"}]}')"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-pass-ne.json" >/dev/null 2>&1; chk "C1 v1 pass+非空→1" 1 $?

# C1-7: 未知/坏 marker → 1
mk_ra_raw "$TD/c1-badmarker.json" '{"severity":"concern","summary":"坏 marker","evidence":[{"ref":"a:1"}],"required_actions_contract":"call-omp.required_actions.v2","required_actions":[{"kind":"revise","reason":"x"}]}'
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-badmarker.json" >/dev/null 2>&1; chk "C1 坏 marker→1" 1 $?

# C1-8: v1 含 allowlist 之外顶层键 → 1，且 stdout 恰为单行结构化 JSON
mk_ra_raw "$TD/c1-extrakey.json" "$(jq -cn --arg m "$V1M" '{severity:"concern",summary:"v1 越权键",evidence:[{ref:"a:1"}],required_actions_contract:$m,required_actions:[{kind:"revise",reason:"x"}],rogue_field:"leak"}')"
GVC=$(bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-extrakey.json" 2>/dev/null); c1_rc=$?
chk "C1 v1 未知顶层键→1" 1 "$c1_rc"
chk "  未知键 gate stdout 恰为单行" 1 "$(printf '%s\n' "$GVC" | grep -c '')"
echo "$GVC" | jq -e 'type=="object" and .ok==false' >/dev/null 2>&1 && chk "  未知键 stdout 单行合法 JSON(ok=false)" y y || chk "  未知键 stdout 单行合法 JSON(ok=false)" y n
echo "$GVC" | jq -e '.missing_fields|index("rogue_field")' >/dev/null 2>&1 && chk "  missing_fields 含越权键 rogue_field" y y || chk "  missing_fields 含越权键 rogue_field" y n

# C1-9: v1 显式含 confidence（属 allowlist）→ 0，不被当未知键
mk_ra_raw "$TD/c1-conf.json" "$(jq -cn --arg m "$V1M" '{severity:"concern",summary:"v1 带 confidence",evidence:[{ref:"a:1"}],reject_instruction:"修",confidence:"high",required_actions_contract:$m,required_actions:[{kind:"revise",reason:"x"}]}')"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/c1-conf.json" >/dev/null 2>&1; chk "C1 v1 含 confidence→0" 0 $?

echo "═══ P2A-static. 显式可信 OMP_BUNDLE_THINKING（off｜inherit｜非法），无运行时能力探测 ═══"
# 契约：off 仅在【监督型 bundle_only Shell】实际执行时注入精确 --thinking off + 持久化 thinking_control；
#   非监督/RPC/ACP/dry-run 一律不受影响；非法值在任何子进程/资源 sidecar 前 exit 3；不再有 --help 探测。

# ── P2A-1: 默认（未设 OMP_BUNDLE_THINKING → inherit）：§21 的直连监督 bo1 与 RPC→Shell 降级 bofb ──
# 两者均无 --thinking argv、thinking_control=inherit（§21 在无 env 下已产出监督态）。
jq -e '.argv|index("--thinking")|not' "$TD/omp-pids-bo1.json" >/dev/null 2>&1 && chk "P2A-1 inherit 直连监督 argv 不含 --thinking" y y || chk "P2A-1 inherit 直连监督 argv 不含 --thinking" y n
chk "  inherit 直连 run.thinking_control=inherit" inherit "$(jq -r '.run.thinking_control' "$TD/omp-state-bo1.json")"
jq -e '.argv|index("--thinking")|not' "$TD/omp-pids-bofb.json" >/dev/null 2>&1 && chk "  inherit 降级监督 argv 不含 --thinking" y y || chk "  inherit 降级监督 argv 不含 --thinking" y n
chk "  inherit 降级 run.thinking_control=inherit" inherit "$(jq -r '.run.thinking_control' "$TD/omp-state-bofb.json")"

# ── P2A-2: OMP_BUNDLE_THINKING=off，直连监督 + RPC→Shell 降级，均注入精确 --thinking off + 状态 off ──
# 2a: 直连监督 Shell
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id p2aoffd >/dev/null 2>&1
OMP_BUNDLE_THINKING=off OMP_BIN="$TD/mock-omp-witness.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2aoffd.json" >/dev/null 2>&1; chk "P2A-2a off 直连监督 send→0" 0 $?
for _ in $(seq 1 80); do [[ -f "$TD/omp-raw-p2aoffd.json.exit" ]] && break; sleep 0.1; done
jq -e '.argv as $a | ($a|index("--thinking")) as $i | ($i!=null and $a[$i+1]=="off")' "$TD/omp-pids-p2aoffd.json" >/dev/null 2>&1 && chk "  off 直连 argv 含精确 --thinking off" y y || chk "  off 直连 argv 含精确 --thinking off" y n
jq -e '.argv as $a | ($a|index("--thinking")) < ($a|index("--append-system-prompt"))' "$TD/omp-pids-p2aoffd.json" >/dev/null 2>&1 && chk "  --thinking off 在 --append-system-prompt 之前" y y || chk "  --thinking off 在 --append-system-prompt 之前" y n
chk "  off 直连 run.thinking_control=off" off "$(jq -r '.run.thinking_control' "$TD/omp-state-p2aoffd.json")"
# 2b: bundle_only 起始 rpc，RPC 失败降级 Shell → 降级路径同样遵循 off
echo "$BOP_RPC" | OMP_BIN="$TD/mock-bo-degrade.sh" bash "$S/omp-start.sh" --package-json - --task-id p2aofffb >/dev/null 2>&1
OMP_BUNDLE_THINKING=off OMP_BIN="$TD/mock-bo-degrade.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2aofffb.json" --max-time 10 >/dev/null 2>&1; chk "P2A-2b off RPC→Shell 降级 send→0" 0 $?
for _ in $(seq 1 80); do [[ -f "$TD/omp-raw-p2aofffb.json.exit" ]] && break; sleep 0.1; done
chk "  off 降级 channel_used=shell" shell "$(jq -r '.run.channel_used' "$TD/omp-state-p2aofffb.json")"
jq -e '.argv as $a | ($a|index("--thinking")) as $i | ($i!=null and $a[$i+1]=="off")' "$TD/omp-pids-p2aofffb.json" >/dev/null 2>&1 && chk "  off 降级 argv 含精确 --thinking off" y y || chk "  off 降级 argv 含精确 --thinking off" y n
chk "  off 降级 run.thinking_control=off" off "$(jq -r '.run.thinking_control' "$TD/omp-state-p2aofffb.json")"

# ── P2A-3: 即便 env=off，非 bundle_only Shell / RPC daemon / ACP / dry-run 一律不受影响 ──
# 3a: 常规非 bundle_only Shell（同步、无 thinking_control）
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p2anb >/dev/null 2>&1
OMP_BUNDLE_THINKING=off OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2anb.json" >/dev/null 2>&1; chk "P2A-3a 非 bundle_only shell(env off) send→0" 0 $?
chk "  非 bundle_only mode=sync（未误监督）" sync "$(jq -r '.run.mode' "$TD/omp-state-p2anb.json")"
chk "  非 bundle_only 无 thinking_control（null）" null "$(jq -r '.run.thinking_control' "$TD/omp-state-p2anb.json")"
# 3b: RPC daemon（channel_used=rpc、无 thinking_control）
echo "$GP" | jq '.channel="rpc"' | bash "$S/omp-start.sh" --package-json - --task-id p2arpc >/dev/null 2>&1
OMP_BUNDLE_THINKING=off OMP_BIN="$TD/mock-rpc.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2arpc.json" --max-time 30 >/dev/null 2>&1
chk "P2A-3b RPC daemon channel_used=rpc" rpc "$(jq -r '.run.channel_used' "$TD/omp-state-p2arpc.json")"
chk "  RPC daemon 无 thinking_control（null）" null "$(jq -r '.run.thinking_control' "$TD/omp-state-p2arpc.json")"
# 3c: ACP 通道（pending_acp、无 thinking_control）
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p2aacp >/dev/null 2>&1
OMP_BUNDLE_THINKING=off bash "$S/omp-send.sh" --state "$TD/omp-state-p2aacp.json" --channel acp >/dev/null 2>&1; chk "P2A-3c ACP send(env off)→0" 0 $?
chk "  ACP status=pending_acp" pending_acp "$(jq -r '.status' "$TD/omp-state-p2aacp.json")"
chk "  ACP 无 thinking_control（null）" null "$(jq -r '.run.thinking_control' "$TD/omp-state-p2aacp.json")"
# 3d: bundle_only dry-run（env off）：不落任何资源 sidecar、不调 mock、状态仍 gated、输出不含 --thinking
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id p2adry >/dev/null 2>&1
rm -f "$TD/omp-witness.log"
DRYOUT=$(OMP_BUNDLE_THINKING=off OMP_BIN="$TD/mock-omp-witness.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2adry.json" --dry-run 2>/dev/null); chk "P2A-3d bundle_only dry-run(env off)→0" 0 $?
[[ ! -f "$TD/omp-witness.log" ]] && chk "  dry-run 未调用 mock" y y || chk "  dry-run 未调用 mock" y n
[[ ! -f "$TD/omp-resource-p2adry.json" && ! -f "$TD/omp-pids-p2adry.json" ]] && chk "  dry-run 无资源 sidecar" y y || chk "  dry-run 无资源 sidecar" y n
chk "  dry-run 仍 gated（未改状态）" gated "$(jq -r '.status' "$TD/omp-state-p2adry.json")"
echo "$DRYOUT" | grep -q -- "--thinking" && chk "  dry-run 输出不含 --thinking" y n || chk "  dry-run 输出不含 --thinking" y y

# ── P2A-4: 非法 OMP_BUNDLE_THINKING（turbo）在任何子进程/资源 sidecar 前 exit 3 且记录明确原因 ──
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id p2abad >/dev/null 2>&1
rm -f "$TD/omp-witness.log"
OMP_BUNDLE_THINKING=turbo OMP_BIN="$TD/mock-omp-witness.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2abad.json" >/dev/null 2>&1; chk "P2A-4 非法值 send→exit 3" 3 $?
chk "  非法值 status=rejected" rejected "$(jq -r '.status' "$TD/omp-state-p2abad.json")"
jq -r '.gate.reason' "$TD/omp-state-p2abad.json" 2>/dev/null | grep -q "OMP_BUNDLE_THINKING" && chk "  非法值 gate.reason 指明 OMP_BUNDLE_THINKING" y y || chk "  非法值 gate.reason 指明 OMP_BUNDLE_THINKING" y n
[[ ! -f "$TD/omp-witness.log" ]] && chk "  非法值未启动任何子进程（mock 未调）" y y || chk "  非法值未启动任何子进程（mock 未调）" y n
[[ ! -f "$TD/omp-resource-p2abad.json" && ! -f "$TD/omp-pids-p2abad.json" ]] && chk "  非法值无资源 sidecar" y y || chk "  非法值无资源 sidecar" y n
# 非法值为全局 operator-config 门：即便非 bundle_only 通道亦 exit 3（绝不静默纠正）
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id p2abad2 >/dev/null 2>&1
OMP_BUNDLE_THINKING=turbo OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2abad2.json" >/dev/null 2>&1; chk "  非法值（非 bundle 通道）亦 exit 3" 3 $?

# ── P2A-5: off + 子进程拒绝未知 --thinking → 正常监督型 fail-closed 拒绝路径（可归因，无隐藏回退）──
cat > "$TD/mock-omp-thinkreject.sh" <<'M'
#!/usr/bin/env bash
# 模拟未来/旧 OMP 不认识 --thinking：见到即报错并非零退出，绝不产出合法审计。
for a in "$@"; do
  if [[ "$a" == "--thinking" ]]; then
    echo "omp: unknown option --thinking" >&2
    echo reject >> "${OMP_TMPDIR:-/tmp}/omp-thinkreject.log"
    exit 64
  fi
done
# 未带 --thinking 不应发生——若发生，记为隐藏回退证据
echo fallback-invoked >> "${OMP_TMPDIR:-/tmp}/omp-thinkreject.log"
printf '%s\n' '{"type":"turn_end","message":{"role":"assistant","stopReason":"stop"}}'
M
chmod +x "$TD/mock-omp-thinkreject.sh"
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id p2arej >/dev/null 2>&1
rm -f "$TD/omp-thinkreject.log"
OMP_BUNDLE_THINKING=off OMP_TMPDIR="$TD" OMP_BIN="$TD/mock-omp-thinkreject.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-p2arej.json" >/dev/null 2>&1; chk "P2A-5 off+拒绝 mock 监督 send→0（已发起）" 0 $?
chk "  off 拒绝路径 run.thinking_control=off" off "$(jq -r '.run.thinking_control' "$TD/omp-state-p2arej.json")"
for _ in $(seq 1 80); do [[ -f "$TD/omp-raw-p2arej.json.exit" ]] && break; sleep 0.1; done
jq -e '.argv as $a | ($a|index("--thinking")) as $i | ($i!=null and $a[$i+1]=="off")' "$TD/omp-pids-p2arej.json" >/dev/null 2>&1 && chk "  拒绝路径子进程 argv 仍含 --thinking off" y y || chk "  拒绝路径子进程 argv 仍含 --thinking off" y n
chk "  supervisor .exit=4（子进程非零退出，可归因）" 4 "$(cat "$TD/omp-raw-p2arej.json.exit" 2>/dev/null)"
chk "  资源 state 记录子进程 exit_code=64" 64 "$(jq -r '.run.exit_code' "$TD/omp-resource-p2arej.json" 2>/dev/null)"
[[ "$(grep -c reject "$TD/omp-thinkreject.log" 2>/dev/null)" == "1" ]] && chk "  子进程恰被调用一次并拒绝" y y || chk "  子进程恰被调用一次并拒绝" y n
grep -q fallback-invoked "$TD/omp-thinkreject.log" 2>/dev/null && chk "  无隐藏回退（未去掉 flag 重试）" y n || chk "  无隐藏回退（未去掉 flag 重试）" y y

# ── P2A-6: 回归护栏——omp-send.sh 已彻底移除运行时能力探测（不得复活 probe/helper/--help 发现）──
grep -Eq 'thinking_probe|THINKING_PROBE_PY|omp-thinkprobe' "$S/omp-send.sh" && chk "P2A-6 omp-send.sh 无能力探测残留" y n || chk "P2A-6 omp-send.sh 无能力探测残留" y y

echo "═══ P2B S2. verdict_v1 capture 接线 send/monitor（mock-only E2E）═══"
# 全程零真实 OMP/网络/token：直连隔离 mock 经真实 supervisor 跑 verdict_v1，或直接构造 capture
# forensic state + raw/diag sidecar 跑 monitor。py-rec 包裹记录 supervisor 精确 argv。
cat > "$TD/py-rec.sh" <<'M'
#!/usr/bin/env bash
# 记录 supervisor 精确 argv（空格连接足以 grep 精确子串），再 exec 真实 python3。
echo "$*" >> "${PYREC_LOG:-/dev/null}"
exec python3 "$@"
M
chmod +x "$TD/py-rec.sh"
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }

# capture forensic state（verdict_v1 reported）：字段与磁盘 raw/diag 完全自洽。$3=可选 jq override。
mk_cap_res() { local id="$1" st="${2:-reported}" ov="${3:-.}"
  local raw="$TD/omp-raw-$id.json" diag="$TD/omp-raw-$id.json.diag.jsonl"
  local rb rl rs db dl ds
  rb=$(wc -c <"$raw"|tr -d ' '); rl=$(wc -l <"$raw"|tr -d ' '); rs=$(sha256f "$raw")
  db=$(wc -c <"$diag"|tr -d ' '); dl=$(wc -l <"$diag"|tr -d ' '); ds=$(sha256f "$diag")
  jq -n --arg id "$id" --arg raw "$raw" --arg sf "$TD/omp-resource-$id.json" --arg ps "$TD/omp-pids-$id.json" \
        --arg diag "$diag" --arg st "$st" \
        --argjson rb "$rb" --argjson rl "$rl" --arg rs "$rs" --argjson db "$db" --argjson dl "$dl" --arg ds "$ds" \
    '{schema:"call-omp-resource-supervisor.v1",task_id:$id,task_id_source:"test",
      state_file:$sf,raw_output:$raw,raw_cap:2000000,
      raw_bytes:$rb,raw_lines:$rl,raw_sha256:$rs,raw_tail_bytes:$rb,
      rate_fuse:{enabled:false},status:$st,reason:"normal_completion",
      run:{started_at:"t",ended_at:"t",exit_code:0,pid_store:$ps},
      child_identity:{pid:5,pgid:5,session_id:5,argv:["omp"]},
      capture_mode:"verdict_v1",diagnostic_output:$diag,
      ingress_bytes:$rb,ingress_lines:$rl,ingress_sha256:$rs,
      verdict_bytes:$rb,verdict_lines:$rl,verdict_sha256:$rs,
      diagnostic_bytes:$db,diagnostic_lines:$dl,diagnostic_sha256:$ds,
      diagnostic_truncated:false,preserved_count:1,denied_count:0,
      unknown_count:0,terminal_capable_unknown_count:0}' \
    | jq --arg hex "$HEX64" "$ov" > "$TD/omp-resource-$id.json"
}
# capture 主状态（resource_supervised + capture_mode + 规范 diagnostic_output）。
mk_cap_main() { local id="$1"
  jq -n --arg id "$id" --arg raw "$TD/omp-raw-$id.json" --arg rs "$TD/omp-resource-$id.json" \
        --arg ps "$TD/omp-pids-$id.json" --arg diag "$TD/omp-raw-$id.json.diag.jsonl" \
    '{task_id:$id,status:"running",package:{mode:"audit"},
      run:{channel_used:"shell",mode:"async",raw_output:$raw,
           resource_supervised:true,watch_required:true,
           capture_mode:"verdict_v1",diagnostic_output:$diag,
           resource_state:$rs,pid_store:$ps,pid:999999,round:1}}' > "$TD/omp-state-$id.json"
}
# 合法 verdict raw（含 canary 于 summary——若被误解析必现形）+ 2 条 diag preserve 记录。
mk_cap_files() { local id="$1"
  printf '%s\n' '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"concern\",\"summary\":\"S2_RAW_LEAK_CANARY\",\"evidence\":[{\"type\":\"file\",\"ref\":\"x:1\"}]}\n```"}]}}' \
                 '{"type":"turn_end","message":{"stopReason":"stop"}}' > "$TD/omp-raw-$id.json"
  printf '%s\n' '{"decision":"preserve","seq":1}' '{"decision":"preserve","seq":2}' > "$TD/omp-raw-$id.json.diag.jsonl"
}
cap_setup() { local id="$1"; mk_cap_files "$id"; mk_cap_main "$id"; mk_cap_res "$id"; mk_pids "$TD/omp-pids-$id.json" 5 5 5; printf '0\n' > "$TD/omp-raw-$id.json.exit"; }
# 通用 capture-reject 断言：monitor exit 2 + 主 rejected + 未解析(无 severity) + canary 未泄漏。
cap_reject_chk() { local id="$1" label="$2"
  bash "$S/omp-monitor.sh" --state "$TD/omp-state-$id.json" >/dev/null 2>&1; chk "${label} →exit 2" 2 $?
  chk "  [$id] 主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-$id.json")"
  chk "  [$id] 未走判决解析(无 severity)" null "$(jq -r '.monitor.severity // "null"' "$TD/omp-state-$id.json")"
  grep -q S2_RAW_LEAK_CANARY "$TD/omp-state-$id.json" && chk "  [$id] raw 正文未拷入 state" n y || chk "  [$id] raw 正文未拷入 state" n n
}

# ── S2-1: 直连 bundle_only Shell → 经真实 supervisor verdict_v1；argv 精确 caps + 主状态 capture + monitor 报 v1 判决（sanitized raw）──
cat > "$TD/mock-omp-s2sani.sh" <<'M'
#!/usr/bin/env bash
# thinking 流（deny，含 canary，绝不进 verdict raw）+ 合法审计 + 收尾。
printf '%s\n' \
  '{"type":"message_update","assistantMessageEvent":{"type":"thinking","text":"S2_THINK_LEAK_CANARY 秘密推理"}}' \
  '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"```json\n{\"severity\":\"concern\",\"summary\":\"s2 sanitized 审计\",\"evidence\":[{\"type\":\"file\",\"ref\":\"z:1\"}]}\n```"}]}}' \
  '{"type":"turn_end","message":{"role":"assistant","stopReason":"stop"}}'
M
chmod +x "$TD/mock-omp-s2sani.sh"
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id s2d1 >/dev/null 2>&1
PYREC_LOG="$TD/s2d1-pyargv.log"; rm -f "$PYREC_LOG"
PYREC_LOG="$PYREC_LOG" OMP_PY="$TD/py-rec.sh" OMP_BIN="$TD/mock-omp-s2sani.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-s2d1.json" >/dev/null 2>&1; chk "S2-1 直连 bundle_only send→0" 0 $?
chk "  主状态 run.capture_mode=verdict_v1" verdict_v1 "$(jq -r '.run.capture_mode' "$TD/omp-state-s2d1.json")"
chk "  主状态 run.diagnostic_output 规范" "$TD/omp-raw-s2d1.json.diag.jsonl" "$(jq -r '.run.diagnostic_output' "$TD/omp-state-s2d1.json")"
for _ in $(seq 1 80); do [[ -f "$TD/omp-raw-s2d1.json.exit" ]] && break; sleep 0.1; done
chk "  supervisor .exit=0" 0 "$(cat "$TD/omp-raw-s2d1.json.exit" 2>/dev/null)"
# argv 断言在 .exit 落盘后（py-rec 于 exec 前已记录，此时必已写入），杜绝与后台监督器竞态。
grep -q -- "--capture-mode verdict_v1" "$PYREC_LOG" && chk "  supervisor argv 含 --capture-mode verdict_v1" y y || chk "  supervisor argv 含 --capture-mode verdict_v1" y n
grep -q -- "--ingress-cap 134217728" "$PYREC_LOG" && chk "  supervisor argv 含 --ingress-cap 134217728" y y || chk "  supervisor argv 含 --ingress-cap 134217728" y n
grep -q -- "--verdict-cap 1048576" "$PYREC_LOG" && chk "  supervisor argv 含 --verdict-cap 1048576" y y || chk "  supervisor argv 含 --verdict-cap 1048576" y n
grep -q -- "--diagnostic-cap 524288" "$PYREC_LOG" && chk "  supervisor argv 含 --diagnostic-cap 524288" y y || chk "  supervisor argv 含 --diagnostic-cap 524288" y n
chk "  资源 state status=reported" reported "$(jq -r '.status' "$TD/omp-resource-s2d1.json" 2>/dev/null)"
chk "  资源 state capture_mode=verdict_v1" verdict_v1 "$(jq -r '.capture_mode' "$TD/omp-resource-s2d1.json" 2>/dev/null)"
[[ -f "$TD/omp-raw-s2d1.json.diag.jsonl" ]] && chk "  diag sidecar 落盘" y y || chk "  diag sidecar 落盘" y n
grep -q S2_THINK_LEAK_CANARY "$TD/omp-raw-s2d1.json" && chk "  sanitized：thinking canary 未进 verdict raw" n y || chk "  sanitized：thinking canary 未进 verdict raw" n n
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s2d1.json" >/dev/null 2>&1; chk "  monitor→reported(0)" 0 $?
chk "  monitor severity=concern（经 sanitized verdict raw）" concern "$(jq -r '.monitor.severity' "$TD/omp-state-s2d1.json")"
chk "  monitor.capture.capture_mode=verdict_v1" verdict_v1 "$(jq -r '.monitor.capture.capture_mode' "$TD/omp-state-s2d1.json")"
chk "  monitor.capture.denied_count=1（thinking 被 deny）" 1 "$(jq -r '.monitor.capture.denied_count' "$TD/omp-state-s2d1.json")"
chk "  monitor.capture 无 raw 正文/argv（仅数值/hash 子集）" false "$(jq -r '.monitor.capture|(has("argv") or has("tail") or has("raw_tail_bytes"))' "$TD/omp-state-s2d1.json")"
grep -q S2_THINK_LEAK_CANARY "$TD/omp-state-s2d1.json" && chk "  thinking canary 未泄漏进主 state" n y || chk "  thinking canary 未泄漏进主 state" n n

# ── S2-2: RPC→Shell 降级 → 同样 verdict_v1 capture argv/state，monitor 成功 ──
echo "$BOP" | jq '.channel="rpc"' | bash "$S/omp-start.sh" --package-json - --task-id s2fb >/dev/null 2>&1
PYREC_LOG="$TD/s2fb-pyargv.log"; rm -f "$PYREC_LOG"
PYREC_LOG="$PYREC_LOG" OMP_PY="$TD/py-rec.sh" OMP_BIN="$TD/mock-bo-degrade.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-s2fb.json" --max-time 10 >/dev/null 2>&1; chk "S2-2 RPC→Shell 降级 send→0" 0 $?
chk "  降级 channel_used=shell" shell "$(jq -r '.run.channel_used' "$TD/omp-state-s2fb.json")"
chk "  降级 run.capture_mode=verdict_v1" verdict_v1 "$(jq -r '.run.capture_mode' "$TD/omp-state-s2fb.json")"
chk "  降级 run.diagnostic_output 规范" "$TD/omp-raw-s2fb.json.diag.jsonl" "$(jq -r '.run.diagnostic_output' "$TD/omp-state-s2fb.json")"
for _ in $(seq 1 80); do [[ -f "$TD/omp-raw-s2fb.json.exit" ]] && break; sleep 0.1; done
grep -q -- "--capture-mode verdict_v1" "$PYREC_LOG" && chk "  降级 supervisor argv 含 capture caps" y y || chk "  降级 supervisor argv 含 capture caps" y n
grep -q -- "--ingress-cap 134217728" "$PYREC_LOG" && grep -q -- "--verdict-cap 1048576" "$PYREC_LOG" && grep -q -- "--diagnostic-cap 524288" "$PYREC_LOG" && chk "  降级 supervisor argv 三 cap 齐全" y y || chk "  降级 supervisor argv 三 cap 齐全" y n
chk "  降级 资源 state status=reported" reported "$(jq -r '.status' "$TD/omp-resource-s2fb.json" 2>/dev/null)"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s2fb.json" >/dev/null 2>&1; chk "  降级 monitor→reported(0)" 0 $?
chk "  降级 monitor severity=nit" nit "$(jq -r '.monitor.severity' "$TD/omp-state-s2fb.json")"
chk "  降级 monitor.capture.capture_mode=verdict_v1" verdict_v1 "$(jq -r '.monitor.capture.capture_mode' "$TD/omp-state-s2fb.json")"

# ── S2-3: 非 capture 通道零 capture 泄漏（无 capture 主状态字段、无 capture argv、无 diag sidecar）──
# 3a 普通(非 bundle_only) shell：无 supervisor、无 capture
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id s2ns >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-s2ns.json" >/dev/null 2>&1; chk "S2-3a 非 bundle shell send→0" 0 $?
chk "  普通 shell run.capture_mode=null" null "$(jq -r '.run.capture_mode' "$TD/omp-state-s2ns.json")"
chk "  普通 shell run.diagnostic_output=null" null "$(jq -r '.run.diagnostic_output' "$TD/omp-state-s2ns.json")"
[[ ! -f "$TD/omp-raw-s2ns.json.diag.jsonl" ]] && chk "  普通 shell 无 diag sidecar" y y || chk "  普通 shell 无 diag sidecar" y n
# 3b RPC daemon 通道：无 capture
echo "$GP" | jq '.channel="rpc"' | bash "$S/omp-start.sh" --package-json - --task-id s2rpc >/dev/null 2>&1
OMP_BIN="$TD/mock-rpc.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-s2rpc.json" --max-time 30 >/dev/null 2>&1; chk "S2-3b RPC daemon send channel_used=rpc" rpc "$(jq -r '.run.channel_used' "$TD/omp-state-s2rpc.json")"
chk "  RPC run.capture_mode=null" null "$(jq -r '.run.capture_mode' "$TD/omp-state-s2rpc.json")"
[[ ! -f "$TD/omp-raw-s2rpc.json.diag.jsonl" ]] && chk "  RPC 无 diag sidecar" y y || chk "  RPC 无 diag sidecar" y n
RDP=$(jq -r '.run.rpc_pid // empty' "$TD/omp-state-s2rpc.json"); [[ -n "$RDP" ]] && kill "$RDP" 2>/dev/null
# 3c ACP 通道：pending_acp、无 capture
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id s2acp >/dev/null 2>&1
OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-s2acp.json" --channel acp >/dev/null 2>&1; chk "S2-3c ACP send→pending_acp" pending_acp "$(jq -r '.status' "$TD/omp-state-s2acp.json")"
chk "  ACP run.capture_mode=null" null "$(jq -r '.run.capture_mode' "$TD/omp-state-s2acp.json")"
[[ ! -f "$TD/omp-raw-s2acp.json.diag.jsonl" ]] && chk "  ACP 无 diag sidecar" y y || chk "  ACP 无 diag sidecar" y n
# 3d dry-run：bundle 描述 capture 但零 sidecar/子进程；非监督通道 dry-run 输出不含 capture argv
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id s2dry >/dev/null 2>&1
DRYOUT=$(OMP_BIN="$TD/mock-omp-witness.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-s2dry.json" --dry-run 2>/dev/null); chk "S2-3d bundle dry-run→0" 0 $?
chk "  dry-run 仍 gated" gated "$(jq -r '.status' "$TD/omp-state-s2dry.json")"
echo "$DRYOUT" | grep -q -- "--capture-mode verdict_v1" && chk "  bundle dry-run 描述 capture argv" y y || chk "  bundle dry-run 描述 capture argv" y n
[[ ! -f "$TD/omp-resource-s2dry.json" && ! -f "$TD/omp-raw-s2dry.json.diag.jsonl" ]] && chk "  dry-run 无资源/diag sidecar" y y || chk "  dry-run 无资源/diag sidecar" y n
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id s2drns >/dev/null 2>&1
DRYNS=$(OMP_BIN="$TD/mock-omp.sh" bash "$S/omp-send.sh" --state "$TD/omp-state-s2drns.json" --dry-run 2>/dev/null)
echo "$DRYNS" | grep -q -- "--capture-mode" && chk "  非 bundle shell dry-run 无 capture argv" y n || chk "  非 bundle shell dry-run 无 capture argv" y y

# ── S2-4: capture 认证各失败面均在判决解析【前】拒绝（fail-closed），canary 不泄漏 ──
# 4a baseline：合法 capture 合成 fixture → monitor 报 concern（证明后续拒绝确因单点变异）
cap_setup s4base
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s4base.json" >/dev/null 2>&1; chk "S2-4a 合法 capture fixture→reported(0)" 0 $?
chk "  baseline severity=concern" concern "$(jq -r '.monitor.severity' "$TD/omp-state-s4base.json")"
chk "  baseline monitor.capture 存在" verdict_v1 "$(jq -r '.monitor.capture.capture_mode' "$TD/omp-state-s4base.json")"
# 4b diag 缺失
cap_setup s4dmiss; rm -f "$TD/omp-raw-s4dmiss.json.diag.jsonl"
cap_reject_chk s4dmiss "S2-4b diag 缺失"
# 4c diag symlink
cap_setup s4dsym; rm -f "$TD/omp-raw-s4dsym.json.diag.jsonl"; printf 'x\n' > "$TD/s4dsym-diagtarget"; ln -s "$TD/s4dsym-diagtarget" "$TD/omp-raw-s4dsym.json.diag.jsonl"
cap_reject_chk s4dsym "S2-4c diag symlink"
# 4d diag 非普通文件（目录）
cap_setup s4ddir; rm -f "$TD/omp-raw-s4ddir.json.diag.jsonl"; mkdir -p "$TD/omp-raw-s4ddir.json.diag.jsonl"
cap_reject_chk s4ddir "S2-4d diag 非普通文件"
# 4e 路径不匹配（资源 diagnostic_output 非规范）
cap_setup s4pm; mk_cap_res s4pm reported '.diagnostic_output="/tmp/evil.diag.jsonl"'
cap_reject_chk s4pm "S2-4e diagnostic_output 路径不匹配"
# 4e2 主状态 capture_mode 缺失（绑定不符）
cap_setup s4pm2; jq 'del(.run.capture_mode)' "$TD/omp-state-s4pm2.json" > "$TD/omp-state-s4pm2.json.t" && mv "$TD/omp-state-s4pm2.json.t" "$TD/omp-state-s4pm2.json"
cap_reject_chk s4pm2 "S2-4e2 主 capture_mode 缺失"
# 4f 字段类型错（verdict_bytes 为 string）
cap_setup s4ft; mk_cap_res s4ft reported '.verdict_bytes="276"'
cap_reject_chk s4ft "S2-4f verdict_bytes 类型错"
# 4g diagnostic_truncated 非布尔
cap_setup s4bt; mk_cap_res s4bt reported '.diagnostic_truncated="no"'
cap_reject_chk s4bt "S2-4g diagnostic_truncated 非布尔"
# 4h hash 格式错（verdict_sha256 非 64hex 而 bytes>0）
cap_setup s4hf; mk_cap_res s4hf reported '.verdict_sha256="deadbeef"'
cap_reject_chk s4hf "S2-4h verdict_sha256 非 64hex"
# 4i count 不符（raw_bytes != verdict_bytes）
cap_setup s4cnt; mk_cap_res s4cnt reported '.raw_bytes=(.raw_bytes+1)'
cap_reject_chk s4cnt "S2-4i raw_bytes!=verdict_bytes"
# 4j raw 磁盘 digest 与 state 不符（state sha 改为不同合法 64hex，磁盘不变）
cap_setup s4rd; mk_cap_res s4rd reported '.raw_sha256=$hex | .verdict_sha256=$hex'
cap_reject_chk s4rd "S2-4j raw 磁盘 sha 不符"
# 4k diag 磁盘 digest 与 state 不符
cap_setup s4dd; mk_cap_res s4dd reported '.diagnostic_sha256=$hex'
cap_reject_chk s4dd "S2-4k diag 磁盘 sha 不符"
# 4l reported 携带 terminal_capable_unknown_count>0（不可信终态）
cap_setup s4tu; mk_cap_res s4tu reported '.unknown_count=1 | .terminal_capable_unknown_count=1'
cap_reject_chk s4tu "S2-4l reported 携带 terminal unknown"

# ── S2-5: legacy 资源 v1（无 capture 字段）monitor 行为逐字节不变（不加 capture 元数据）──
mk_sup_state s5leg
mk_res s5leg reported '.reason="normal_completion" | .raw_bytes=512 | .raw_lines=3 | .raw_sha256=$hex | .raw_tail_bytes=512 | .run.exit_code=0 | .child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-s5leg.json" 5 5 5
"$TD/mock-omp.sh" > "$TD/omp-raw-s5leg.json"; printf '0\n' > "$TD/omp-raw-s5leg.json.exit"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s5leg.json" >/dev/null 2>&1; chk "S2-5 legacy v1（无 capture）→reported(0)" 0 $?
chk "  legacy 主状态 reported" reported "$(jq -r .status "$TD/omp-state-s5leg.json")"
chk "  legacy severity=concern（既有解析不变）" concern "$(jq -r '.monitor.severity' "$TD/omp-state-s5leg.json")"
chk "  legacy 无 monitor.capture（capture 元数据不误加）" null "$(jq -r '.monitor.capture // "null"' "$TD/omp-state-s5leg.json")"
chk "  legacy 资源 state 无 capture_mode" null "$(jq -r '.capture_mode // "null"' "$TD/omp-resource-s5leg.json")"

# ── S2-6（return 1）：跨状态 capture 迁移一致性闸——主状态为迁移权威，堵住降级洞 ──
# 洞：仅凭「资源 capture_mode==verdict_v1」才认证，会让「主已迁移 v1 但资源缺失/异常」被静默当 legacy。
# 契约：main==v1 ⇒ 资源【任意 status】须显式 v1+规范 diag，否则判决解析【前】fail-closed；
#       资源声明 capture 但 main 未声明 ⇒ 拒绝；仅双缺才走 legacy。
# 6a: main=verdict_v1 + 资源 reported 缺 capture_mode → 判决解析前 fail-closed（不当 legacy）
mk_cap_files s6a; mk_cap_main s6a
mk_res s6a reported '.reason="normal_completion" | .raw_bytes=512 | .raw_lines=3 | .raw_sha256=$hex | .raw_tail_bytes=512 | .run.exit_code=0 | .child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-s6a.json" 5 5 5
cap_reject_chk s6a "S2-6a main=v1 + resource 缺 capture_mode(reported)"
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-s6a.json")" == *"迁移不一致"* ]] && chk "  [s6a] issue=capture 迁移不一致" y y || chk "  [s6a] issue=capture 迁移不一致" y n

# 6b: main=verdict_v1 + 资源 reported capture_mode=legacy_v0 → fail-closed（其它非空值不静默当 legacy）
mk_cap_files s6b; mk_cap_main s6b
mk_res s6b reported '.reason="normal_completion" | .raw_bytes=512 | .raw_lines=3 | .raw_sha256=$hex | .raw_tail_bytes=512 | .run.exit_code=0 | .capture_mode="legacy_v0" | .child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-s6b.json" 5 5 5
cap_reject_chk s6b "S2-6b main=v1 + resource capture_mode=legacy_v0(reported)"

# 6c: main=verdict_v1 + 资源 starting 缺 capture_mode → exit 2（不再误判 running；sidecar 就绪也拒绝）
mk_cap_files s6c; mk_cap_main s6c
mk_res s6c starting '.child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-s6c.json" 5 5 5
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s6c.json" >/dev/null 2>&1; chk "S2-6c main=v1 + resource starting 缺 capture→exit 2" 2 $?
chk "  [s6c] 主状态 rejected（非 running）" rejected "$(jq -r .status "$TD/omp-state-s6c.json")"
[[ "$(jq -r '.monitor.issues[0]' "$TD/omp-state-s6c.json")" == *"迁移不一致"* ]] && chk "  [s6c] issue=迁移不一致" y y || chk "  [s6c] issue=迁移不一致" y n

# 6d: 资源 verdict_v1 但 main 未声明 capture_mode → starting 与 reported 均 reject
mk_sup_state s6dsg   # main legacy（无 capture_mode）
mk_res s6dsg starting '.capture_mode="verdict_v1" | .child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-s6dsg.json" 5 5 5
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s6dsg.json" >/dev/null 2>&1; chk "S2-6d resource=v1 + main 缺 capture(starting)→exit 2" 2 $?
chk "  [s6dsg] 主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-s6dsg.json")"
mk_sup_state s6drg
mk_res s6drg reported '.reason="normal_completion" | .raw_bytes=512 | .raw_lines=3 | .raw_sha256=$hex | .raw_tail_bytes=512 | .run.exit_code=0 | .capture_mode="verdict_v1" | .child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-s6drg.json" 5 5 5
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s6drg.json" >/dev/null 2>&1; chk "S2-6d resource=v1 + main 缺 capture(reported)→exit 2" 2 $?
chk "  [s6drg] 主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-s6drg.json")"
chk "  [s6drg] 未走判决解析(无 severity)" null "$(jq -r '.monitor.severity // "null"' "$TD/omp-state-s6drg.json")"

# 6e: main 与资源【双缺】capture_mode → legacy 路径逐字节不变，仍 reportable(0)
mk_sup_state s6leg
mk_res s6leg reported '.reason="normal_completion" | .raw_bytes=512 | .raw_lines=3 | .raw_sha256=$hex | .raw_tail_bytes=512 | .run.exit_code=0 | .child_identity={pid:5,pgid:5,session_id:5,argv:["omp"]}'
mk_pids "$TD/omp-pids-s6leg.json" 5 5 5
"$TD/mock-omp.sh" > "$TD/omp-raw-s6leg.json"; printf '0\n' > "$TD/omp-raw-s6leg.json.exit"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s6leg.json" >/dev/null 2>&1; chk "S2-6e 双缺 capture legacy→reported(0)" 0 $?
chk "  [s6leg] 主状态 reported" reported "$(jq -r .status "$TD/omp-state-s6leg.json")"
chk "  [s6leg] 无 monitor.capture（不误加）" null "$(jq -r '.monitor.capture // "null"' "$TD/omp-state-s6leg.json")"

# 6f: main=v1 + 资源=v1【一致】的 starting → 正常 running(0)（证明闸不误伤对齐迁移）
mk_cap_files s6f; mk_cap_main s6f; mk_cap_res s6f starting
mk_pids "$TD/omp-pids-s6f.json" 5 5 5
MJ=$(bash "$S/omp-monitor.sh" --state "$TD/omp-state-s6f.json" --json 2>/dev/null); RC=$?
chk "S2-6f main=v1 + resource=v1 一致(starting)→exit 0" 0 $RC
chk "  [s6f] phase=running" running "$(echo "$MJ" | jq -r .phase)"
chk "  [s6f] 主状态仍 running（未被改写）" running "$(jq -r .status "$TD/omp-state-s6f.json")"

# 6g: main.run.capture_mode 未知非空值 → 顶层 fail-closed（不进资源块/legacy）
mk_cap_files s6g; mk_cap_main s6g; mk_cap_res s6g reported
jq '.run.capture_mode="legacy_v0"' "$TD/omp-state-s6g.json" > "$TD/omp-state-s6g.json.t" && mv "$TD/omp-state-s6g.json.t" "$TD/omp-state-s6g.json"
mk_pids "$TD/omp-pids-s6g.json" 5 5 5
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s6g.json" >/dev/null 2>&1; chk "S2-6g main 未知 capture_mode→exit 2" 2 $?
chk "  [s6g] 主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-s6g.json")"
grep -q S2_RAW_LEAK_CANARY "$TD/omp-state-s6g.json" && chk "  [s6g] raw 正文未拷入 state" n y || chk "  [s6g] raw 正文未拷入 state" n n

# 6h: main=verdict_v1 但非 resource_supervised → 无监督器无法认证 capture → 顶层 fail-closed
mk_cap_files s6h; mk_cap_main s6h
jq '.run.resource_supervised=false' "$TD/omp-state-s6h.json" > "$TD/omp-state-s6h.json.t" && mv "$TD/omp-state-s6h.json.t" "$TD/omp-state-s6h.json"
bash "$S/omp-monitor.sh" --state "$TD/omp-state-s6h.json" >/dev/null 2>&1; chk "S2-6h main=v1 非 resource_supervised→exit 2" 2 $?
chk "  [s6h] 主状态 rejected" rejected "$(jq -r .status "$TD/omp-state-s6h.json")"

echo "═══ P0B1-A. atomic_write 0600 + 每任务启动锁 + 复用/残留拒绝（零 token）═══"
# 全程零真实 OMP/网络/token：全部走 gate + 状态文件，OMP_BIN 为隔离 mock（可用即可）。
fmode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1" 2>/dev/null; }

# A1: omp-start 落盘的 package/state 均为 0600（atomic_write 私有化）
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa1 >/dev/null 2>&1; chk "A1 start→gated" gated "$(jq -r .status "$TD/omp-state-sa1.json")"
chk "  state 权限 0600" 600 "$(fmode "$TD/omp-state-sa1.json")"
chk "  package 权限 0600" 600 "$(fmode "$TD/omp-pkg-sa1.json")"
# 直接单元验证 atomic_write：任意目标落盘即 0600，内容正确
( source "$S/lib/omp-lib.sh"; echo hi | atomic_write "$TD/aw-probe.txt" )
chk "  atomic_write 目标 0600" 600 "$(fmode "$TD/aw-probe.txt")"
chk "  atomic_write 内容正确" hi "$(cat "$TD/aw-probe.txt")"
# 预置宽权限目标，atomic_write 覆盖后必须收敛为 0600（final target 0600）
printf 'old\n' > "$TD/aw-wide.txt"; chmod 0666 "$TD/aw-wide.txt"
( source "$S/lib/omp-lib.sh"; echo new | atomic_write "$TD/aw-wide.txt" )
chk "  覆盖宽权限收敛 0600" 600 "$(fmode "$TD/aw-wide.txt")"
chk "  覆盖后内容更新（原子替换保持）" new "$(cat "$TD/aw-wide.txt")"

# A2: 启动锁被占用 → 拒绝 exit 3，不写 state；释放后可正常 start 且退出即释放锁
mkdir -p "$TD/omp-start-sa2.lock"   # 模拟并发 start 持锁
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa2 >/dev/null 2>&1; chk "A2 启动锁占用→exit 3" 3 $?
[[ ! -f "$TD/omp-state-sa2.json" ]] && chk "  锁占用未写 state" y y || chk "  锁占用未写 state" y n
rmdir "$TD/omp-start-sa2.lock"
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa2 >/dev/null 2>&1; chk "  释放后 start→0" 0 $?
[[ ! -d "$TD/omp-start-sa2.lock" ]] && chk "  正常退出已释放启动锁" y y || chk "  正常退出已释放启动锁" y n

# A3: live-running 复用拒绝（status=running）→ exit 3，state 字节不变、进程仍存活未解链
sleep 300 & LIVEPID=$!
jq -n --argjson p "$LIVEPID" '{task_id:"sa3",status:"running",package:{mode:"audit"},run:{channel_used:"shell",mode:"async",resource_supervised:false,pid:$p}}' > "$TD/omp-state-sa3.json"
SHA_BEFORE=$(shasum "$TD/omp-state-sa3.json" | awk '{print $1}')
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa3 >/dev/null 2>&1; chk "A3 status=running 复用→exit 3" 3 $?
chk "  running state 字节不变" "$SHA_BEFORE" "$(shasum "$TD/omp-state-sa3.json" | awk '{print $1}')"
kill -0 "$LIVEPID" 2>/dev/null && chk "  running 进程仍存活（未被解链）" y y || chk "  running 进程仍存活（未被解链）" y n
[[ ! -f "$TD/omp-pkg-sa3.json" ]] && chk "  running 复用未写 package" y y || chk "  running 复用未写 package" y n
kill "$LIVEPID" 2>/dev/null || true

# A3b: resource_supervised=true + supervisor PID 存活（status 非 running）→ 仍拒绝
sleep 300 & SUPPID=$!
jq -n --argjson p "$SUPPID" '{task_id:"sa3b",status:"reported",package:{mode:"audit"},run:{channel_used:"shell",mode:"async",resource_supervised:true,pid:$p}}' > "$TD/omp-state-sa3b.json"
SHAB=$(shasum "$TD/omp-state-sa3b.json" | awk '{print $1}')
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa3b >/dev/null 2>&1; chk "A3b supervised+live PID 复用→exit 3" 3 $?
chk "  supervised state 字节不变" "$SHAB" "$(shasum "$TD/omp-state-sa3b.json" | awk '{print $1}')"
kill -0 "$SUPPID" 2>/dev/null && chk "  supervisor 进程仍存活（未被解链）" y y || chk "  supervisor 进程仍存活（未被解链）" y n
kill "$SUPPID" 2>/dev/null || true

# A3c: supervised=true 但 supervisor PID 已死 → 允许重试（回归 legacy 非 live 复用语义）
sleep 0.1 & DEADPID=$!; wait "$DEADPID" 2>/dev/null || true
jq -n --argjson p "$DEADPID" '{task_id:"sa3c",status:"reported",package:{mode:"audit"},run:{channel_used:"shell",mode:"async",resource_supervised:true,pid:$p}}' > "$TD/omp-state-sa3c.json"
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa3c >/dev/null 2>&1; chk "A3c supervised+死 PID→允许重试(0)" 0 $?
chk "  重试后 status=gated" gated "$(jq -r .status "$TD/omp-state-sa3c.json")"

# A4: bundle_only 需全新 task_id —— 任一残留产物存在即拒绝且不改动残留、不误写 state
for art in state pkg raw resource pids launch; do
  id="sa4$art"
  case "$art" in
    state)    f="$TD/omp-state-$id.json" ;;
    pkg)      f="$TD/omp-pkg-$id.json" ;;
    raw)      f="$TD/omp-raw-$id.json" ;;
    resource) f="$TD/omp-resource-$id.json" ;;
    pids)     f="$TD/omp-pids-$id.json" ;;
    launch)   f="$TD/omp-launch-$id.lock" ;;
  esac
  printf 'STALE_%s_CANARY\n' "$art" > "$f"
  SHA=$(shasum "$f" | awk '{print $1}')
  echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id "$id" >/dev/null 2>&1; chk "A4 bundle_only 残留 ${art}→exit 3" 3 $?
  chk "  残留 $art 未被改动（字节不变）" "$SHA" "$(shasum "$f" | awk '{print $1}')"
  if [[ "$art" != "state" ]]; then
    [[ ! -f "$TD/omp-state-$id.json" ]] && chk "  残留 $art 未误写 state" y y || chk "  残留 $art 未误写 state" y n
  fi
  if [[ "$art" != "pkg" ]]; then
    [[ ! -f "$TD/omp-pkg-$id.json" ]] && chk "  残留 $art 未误写 package" y y || chk "  残留 $art 未误写 package" y n
  fi
done
# A4-fresh: 全新 bundle_only task_id（无任何残留）→ 正常 gated，且 state 为 0600
echo "$BOP" | bash "$S/omp-start.sh" --package-json - --task-id sa4fresh >/dev/null 2>&1; chk "A4 全新 bundle_only→gated" gated "$(jq -r .status "$TD/omp-state-sa4fresh.json")"
chk "  bundle_only state 0600" 600 "$(fmode "$TD/omp-state-sa4fresh.json")"

# A5: 普通（非 bundle_only）retry 语义保持——既有 gated、无 live 进程 → 允许覆盖更新
echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa5 >/dev/null 2>&1; chk "A5 首次 start→gated" gated "$(jq -r .status "$TD/omp-state-sa5.json")"
echo "$GP" | jq '.task="审查 auth v2"' | bash "$S/omp-start.sh" --package-json - --task-id sa5 >/dev/null 2>&1; chk "  retry 覆盖→0" 0 $?
chk "  retry 后仍 gated" gated "$(jq -r .status "$TD/omp-state-sa5.json")"
chk "  retry 后 package 已更新" "审查 auth v2" "$(jq -r '.package.task' "$TD/omp-state-sa5.json")"

# A6: 并发 start 同一 task_id 串行安全（无撕裂；至少一个成功；退出后锁已释放；state 合法）
: > "$TD/sa6-rc.log"
for _n in 1 2 3 4 5; do
  ( echo "$GP" | bash "$S/omp-start.sh" --package-json - --task-id sa6 >>"$TD/sa6-rc.log" 2>&1; echo "rc=$?" >> "$TD/sa6-rc.log" ) &
done
wait
OKN=$(grep -c 'rc=0' "$TD/sa6-rc.log" 2>/dev/null)
[[ "${OKN:-0}" -ge 1 ]] && chk "A6 并发 start 至少一个成功" y y || chk "A6 并发 start 至少一个成功" y n
jq -e 'type=="object" and .task_id=="sa6" and .status=="gated"' "$TD/omp-state-sa6.json" >/dev/null 2>&1 && chk "  并发后 state 合法未撕裂" y y || chk "  并发后 state 合法未撕裂" y n
[[ ! -d "$TD/omp-start-sa6.lock" ]] && chk "  并发后启动锁已释放" y y || chk "  并发后启动锁已释放" y n

echo; echo "════════ PASS=$P  FAIL=$F ════════"
[[ $F -eq 0 ]] && exit 0 || exit 1
