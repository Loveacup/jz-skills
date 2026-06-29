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
chmod +x "$S"/*.sh "$S"/gate/*.sh 2>/dev/null

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

GP='{"channel":"shell","mode":"audit","task":"审查 auth","scope":{"allowed_paths":["src/auth"],"denied_paths":[],"cwd":"/tmp/repo"},"criterion":["SQL 参数化"],"threshold":{"round_limit":3,"reject_limit":2},"risk":{"level":"low","dangerous_modes":[]},"auditor":{"required":true,"independence_level":"independent_readonly"},"output":{"format":"json","evidence_required":true}}'
mkpkg(){ echo "$GP" | jq "$1"; }

echo "═══ 1. gate-verify ═══"
mkpkg '.task_id="t-ok"' > "$TD/pkg-ok.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-ok.json" >/dev/null 2>&1; chk "package 齐全→0" 0 $?
mkpkg '.task_id="t-ok"|.criterion=[]' > "$TD/pkg-noc.json"
bash "$S/gate/gate-verify.sh" --mode package --file "$TD/pkg-noc.json" >/dev/null 2>&1; chk "缺 criterion→1" 1 $?
"$TD/mock-omp.sh" > "$TD/raw-ok.json"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-ok.json" >/dev/null 2>&1; chk "output 有 evidence→0" 0 $?
"$TD/mock-noev.sh" > "$TD/raw-noev.json"
bash "$S/gate/gate-verify.sh" --mode output --file "$TD/raw-noev.json" >/dev/null 2>&1; chk "output 空 evidence→10" 10 $?

echo "═══ 2. gate-danger ═══"
bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-ok.json" >/dev/null 2>&1; chk "安全包→0" 0 $?
mkpkg '.mode="clean"|.risk={level:"high",dangerous_modes:["clean"]}' > "$TD/pkg-cl.json"
bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-cl.json" >/dev/null 2>&1; chk "clean 无 rollback→10" 10 $?
mkpkg '.mode="clean"|.risk={level:"high",dangerous_modes:["clean"],rollback:"pg_dump 备份"}' > "$TD/pkg-clok.json"
bash "$S/gate/gate-danger.sh" --mode package --file "$TD/pkg-clok.json" >/dev/null 2>&1; chk "clean 有 rollback→0" 0 $?
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
pkill -f "mock-rpc.sh" 2>/dev/null; pkill -f "mock-degrade.sh" 2>/dev/null

# ════ 13. --watch 模式（v0.5.0 STDD 修复）══════════════════════════
echo "═══ 13. --watch 模式 ═══"

# Setup mock state (ACP channel, so --watch should reject)
cat > /tmp/omp-test-state.json << 'STATEEOF'
{"task_id":"test-watch","status":"running","run":{"channel_used":"acp","raw_output":"/tmp/omp-test-raw.json","max_time":300}}
STATEEOF

# 13a: ACP 拒绝 --watch
echo -n "  🧪 watch-acp-reject ... "
OUT=$(bash scripts/omp-monitor.sh --state /tmp/omp-test-state.json --watch 2>&1) || true
if echo "$OUT" | grep -q "不支持 ACP"; then echo "✅"; else echo "❌ 未检测到 ACP 拒绝 (got: ${OUT:0:80})"; ((F++)); fi

# 13b: --interval 非法值
echo -n "  🧪 watch-bad-interval ... "
bash scripts/omp-monitor.sh --state /tmp/omp-test-state.json --watch --interval abc 2>/dev/null; RC=$?
[[ $RC -eq 3 ]] && echo "✅" || { echo "❌ exit=$RC 期望 3"; ((F++)); }

# 13c: --help 覆盖 --watch
echo -n "  🧪 watch-help ... "
OUT=$(bash scripts/omp-monitor.sh --help 2>&1)
if echo "$OUT" | grep -q "\-\-watch"; then echo "✅"; else echo "❌"; ((F++)); fi

((P+=3))

echo; echo "════════ PASS=$P  FAIL=$F ════════"
[[ $F -eq 0 ]] && exit 0 || exit 1

