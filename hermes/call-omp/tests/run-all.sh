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
OUT=$(bash "$S/omp-monitor.sh" --state /tmp/omp-test-state.json --watch 2>&1) || true
if echo "$OUT" | grep -q "不支持 ACP"; then echo "✅"; else echo "❌ 未检测到 ACP 拒绝 (got: ${OUT:0:80})"; ((F++)); fi

# 13b: --interval 非法值
echo -n "  🧪 watch-bad-interval ... "
bash "$S/omp-monitor.sh" --state /tmp/omp-test-state.json --watch --interval abc 2>/dev/null; RC=$?
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
( cd "$GIT_SRC" && git init -q && git config user.email test@example.com && git config user.name test && printf 'base\n' > README.md && git add README.md && git commit -qm init )
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
bash "$S/omp-finish.sh" --state "$TD/omp-state-ex1.json" --accept >/dev/null 2>&1; chk "execute accept 空证据→0" 0 $?
chk "  状态 accepted" accepted "$(jq -r .status "$TD/omp-state-ex1.json")"

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
# 18g: 缺一份 → check 非零（临时移走 codex 清单再还原）
mv "$CODEX_MF" "$TD/codex-mf.bak"
bash "$CHECK" >/dev/null 2>&1; MISS_RC=$?
mv "$TD/codex-mf.bak" "$CODEX_MF"
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

echo; echo "════════ PASS=$P  FAIL=$F ════════"
[[ $F -eq 0 ]] && exit 0 || exit 1

