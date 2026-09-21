#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# tests/test-resource-supervisor.sh —— P0A supervisor 单元/集成测试
#
# 不烧真 token、不依赖 OMP 在线；只用 python3 + bash + jq。
# 用 OMP_SUP_TMPDIR / OMP_SUP_BIN 隔离 mock 与状态。
# ─────────────────────────────────────────────────────────────────
set -uo pipefail
S="${0%/*}"; S="$(cd "$S" && pwd)"; ROOT="$(cd "$S/.." && pwd)"
PY="${PYTHON_BIN:-/opt/homebrew/bin/python3.12}"
[[ -x "$PY" ]] || PY="${PYTHON_BIN:-python3}"
SUP="$ROOT/scripts/omp-resource-supervisor.py"
$PY -m py_compile "$SUP" 2>&1 | head -5
[[ -x "$PY" ]] || { echo "❌ python3 missing"; exit 1; }

TD="${TMPDIR:-/tmp}/omp-sup-test-$$"
EVDIR="${KEEP_TESTDIR:-/tmp/omp-sup-evidence}/$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$EVDIR"
rm -rf "$TD"; mkdir -p "$TD"
# On EXIT, keep the test dir under EVDIR so callers can inspect failure.
trap 'if [[ -d "$TD" && "$P" == "0" && "$F" == "0" ]]; then rm -rf "$TD"; else if [[ -d "$TD" ]]; then cp -R "$TD" "$EVDIR"/testdir && echo "📂 preserved at $EVDIR/testdir"; fi; fi' EXIT
P=0; F=0
chk(){ if [[ "$2" == "$3" ]]; then echo "  ✅ $1"; P=$((P+1)); else echo "  ❌ $1 exp=[$2] got=[$3]"; F=$((F+1)); fi; }

# ── helpers ──
# Slow producer that streams 1 MiB per 0.1s → ~10 MiB/s, default cap=20 MiB
mk_slow_producer() {
  local target_mib="$1"
  cat > "$TD/producer_${target_mib}.py" <<PY
import os, sys, time
CHUNK = 1024 * 1024
TOTAL = ${target_mib}
for _ in range(TOTAL):
    sys.stdout.buffer.write(b"x" * CHUNK)
    sys.stdout.buffer.flush()
    time.sleep(0.1)
PY
}
mk_slow_producer 25
mk_slow_producer 18
mk_burst_producer() {
  local target_mib="$1"
  cat > "$TD/burst_${target_mib}.py" <<PY
import os, sys
sys.stdout.buffer.write(b"y" * (${target_mib} * 1024 * 1024))
PY
}
mk_burst_producer 19
mk_near_cap_legit() {
  local target_mib="$1"
  cat > "$TD/legit_${target_mib}.py" <<PY
import sys, time
# Slow legitimate stream that ends right under cap
total = ${target_mib}
for i in range(total):
    sys.stdout.buffer.write(b"l" * (1024 * 1024))
    sys.stdout.buffer.flush()
    time.sleep(0.15)
sys.stdout.buffer.write(b"\\n")
PY
}
mk_near_cap_legit 19  # 19 MiB safe under 20 MiB cap
mk_near_cap_legit 22 # 22 MiB exceeds cap

# ── Test 1: 25 MiB slow producer killed before cap reached ──
# ── Test 1: 25 MiB slow producer killed before cap reached ──
echo "═══ T1: 25 MiB slow producer killed before 20 MiB cap ═══"
RAW="$TD/raw-t1.json"; ST="$TD/state-t1.json"; PIDS="$TD/pids-t1.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*1024*1024)) --pid-store "$PIDS" \
  --task-id sup-t1 --task-id-source test \
  -- "$PY" "$TD/producer_25.py" >/dev/null 2>&1
RC=$?
set -e
# Wait briefly for state-file atomic finalization
for _ in $(seq 1 40); do [[ -s "$ST" ]] && break; sleep 0.05; done
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
SIZE=$(stat -f %z "$RAW" 2>/dev/null || stat -c %s "$RAW" 2>/dev/null || echo 0)
LINES=$(wc -l <"$RAW" 2>/dev/null | tr -d ' ')
TAIL=$(jq -r .raw_tail_bytes "$ST" 2>/dev/null || echo 0)
DIGEST=$(jq -r .raw_sha256 "$ST" 2>/dev/null || echo "")
# Compute actual sha256
ACT=$(shasum -a 256 "$RAW" 2>/dev/null | awk '{print $1}' || sha256sum "$RAW" | awk '{print $1}')
chk "T1 status=resource_rejected" "resource_rejected" "$STATUS"
chk "T1 supervisor exit=2" "2" "$RC"
chk "T1 raw <= 20 MiB" "ok" "$([ "$SIZE" -le $((20*1024*1024)) ] && echo ok || echo too_big)"
chk "T1 raw_bytes matches file" "$(jq -r .raw_bytes "$ST")" "$SIZE"
chk "T1 tail <= 8192" "ok" "$([ "$TAIL" -le 8192 ] && echo ok || echo too_big)"
chk "T1 digest matches file" "$ACT" "$DIGEST"
# Verify PGID recorded and process group is gone
PGID=$(jq -r .child_identity.pgid "$ST")
PID=$(jq -r .child_identity.pid "$ST")
if kill -0 "$PID" 2>/dev/null; then chk "T1 child PID gone" gone alive; else chk "T1 child PID gone" gone gone; fi
# Verify state file is JSON-parseable and contains required schema fields
jq -e '.schema == "call-omp-resource-supervisor.v1"' "$ST" >/dev/null 2>&1 && chk "T1 schema=v1" y y || chk "T1 schema=v1" y n

# ── Test 2: ongoing valid JSONL stays below cap ──
echo "═══ T2: 10 MiB legitimate producer finishes normally ═══"
mk_legit() {
  cat > "$TD/legit10.py" <<'PY'
import sys, time
for i in range(10):
    sys.stdout.buffer.write((b'{"type":"message_end","seq":%d}\n' % i))
    sys.stdout.buffer.flush()
    time.sleep(0.05)
PY
}
mk_legit
RAW="$TD/raw-t2.json"; ST="$TD/state-t2.json"; PIDS="$TD/pids-t2.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*1024*1024)) --pid-store "$PIDS" \
  --task-id sup-t2 --task-id-source test \
  -- "$PY" "$TD/legit10.py" >/dev/null 2>&1
RC=$?
set -e
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
LINES=$(jq -r .raw_lines "$ST" 2>/dev/null || echo 0)
RC_EC=$(jq -r .run.exit_code "$ST" 2>/dev/null || echo x)
chk "T2 status=reported" "reported" "$STATUS"
chk "T2 supervisor exit=0" "0" "$RC"
chk "T2 child exit=0" "0" "$RC_EC"
chk "T2 lines==10" "10" "$LINES"

# ── Test 3: near-cap valid payload completes (just under cap) ──
echo "═══ T3: 19 MiB legitimate producer completes just under cap ═══"
RAW="$TD/raw-t3.json"; ST="$TD/state-t3.json"; PIDS="$TD/pids-t3.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*1024*1024)) --pid-store "$PIDS" \
  --task-id sup-t3 --task-id-source test \
  -- "$PY" "$TD/legit_19.py" >/dev/null 2>&1
set -e
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
SIZE=$(stat -f %z "$RAW" 2>/dev/null || stat -c %s "$RAW" 2>/dev/null || echo 0)
chk "T3 status=reported" "reported" "$STATUS"
chk "T3 size > 18 MiB" "ok" "$([ "$SIZE" -gt $((18*1024*1024)) ] && echo ok || echo small)"

# ── Test 4: 22 MiB legitimate producer → resource_rejected ──
echo "═══ T4: 22 MiB legitimate producer hits raw_cap ═══"
RAW="$TD/raw-t4.json"; ST="$TD/state-t4.json"; PIDS="$TD/pids-t4.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*1024*1024)) --pid-store "$PIDS" \
  --task-id sup-t4 --task-id-source test \
  -- "$PY" "$TD/legit_22.py" >/dev/null 2>&1
set -e
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
SIZE=$(stat -f %z "$RAW" 2>/dev/null || stat -c %s "$RAW" 2>/dev/null || echo 0)
REASON=$(jq -r .reason "$ST" 2>/dev/null || echo "")
chk "T4 status=resource_rejected" "resource_rejected" "$STATUS"
chk "T4 size <= 20 MiB" "ok" "$([ "$SIZE" -le $((20*1024*1024)) ] && echo ok || echo too_big)"
echo "$REASON" | grep -q "raw_cap" && chk "T4 reason mentions raw_cap" y y || chk "T4 reason mentions raw_cap" y n

# ── Test 5: digest integrity after resource_rejected ──
echo "═══ T5: SHA-256 of persisted bytes matches digest ═══"
RAW="$TD/raw-t5.json"; ST="$TD/state-t5.json"; PIDS="$TD/pids-t5.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((5*1024*1024)) --pid-store "$PIDS" \
  --task-id sup-t5 --task-id-source test \
  -- "$PY" "$TD/burst_19.py" >/dev/null 2>&1
set -e
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
DIGEST=$(jq -r .raw_sha256 "$ST" 2>/dev/null || echo "")
ACT=$(shasum -a 256 "$RAW" 2>/dev/null | awk '{print $1}')
chk "T5 status=resource_rejected" "resource_rejected" "$STATUS"
chk "T5 digest matches actual file" "$ACT" "$DIGEST"

# ── Test 6: rate fuse (window=1MiB, 2 consecutive windows → kill) ──
echo "═══ T6: rate fuse trips after N consecutive over-cap windows ═══"
mk_burst_each_step() {
  cat > "$TD/bursts.py" <<'PY'
import sys, time
# emit ~3 MiB/s in 0.5s steps → 1.5 MiB per window when window_seconds=0.5
for i in range(10):
    sys.stdout.buffer.write(b"z" * (1536 * 1024))
    sys.stdout.buffer.flush()
    time.sleep(0.5)
PY
}
mk_burst_each_step
RAW="$TD/raw-t6.json"; ST="$TD/state-t6.json"; PIDS="$TD/pids-t6.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((50*1024*1024)) --pid-store "$PIDS" \
  --rate-window-bytes $((1024*1024)) \
  --rate-window-seconds 0.5 \
  --rate-fuse-windows 2 \
  --task-id sup-t6 --task-id-source test \
  -- "$PY" "$TD/bursts.py" >/dev/null 2>&1
RC=$?
set -e
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
REASON=$(jq -r .reason "$ST" 2>/dev/null || echo "")
chk "T6 status=resource_rejected" "resource_rejected" "$STATUS"
chk "T6 supervisor exit=2" "2" "$RC"
echo "$REASON" | grep -q "rate_fuse" && chk "T6 reason mentions rate_fuse" y y || chk "T6 reason mentions rate_fuse" y n
# state.raw_bytes must equal the actual on-disk size, digest must match, and
# the file must be at/under cap — the state must describe the real file.
SIZE=$(stat -f %z "$RAW" 2>/dev/null || stat -c %s "$RAW" 2>/dev/null || echo 0)
RBYTES=$(jq -r .raw_bytes "$ST" 2>/dev/null || echo -1)
DIGEST=$(jq -r .raw_sha256 "$ST" 2>/dev/null || echo "")
ACT=$(shasum -a 256 "$RAW" 2>/dev/null | awk '{print $1}' || sha256sum "$RAW" | awk '{print $1}')
chk "T6 raw_bytes == on-disk size" "$SIZE" "$RBYTES"
chk "T6 raw <= 50 MiB cap" "ok" "$([ "$SIZE" -le $((50*1024*1024)) ] && echo ok || echo too_big)"
chk "T6 digest matches file" "$ACT" "$DIGEST"
# Containment: the rate-fused child must be gone by the time the supervisor
# reports resource_rejected. Record its PID (sidecar = state/pid-store) and
# prove the process is dead — this catches the P0B1 bug where rate_fuse set
# the terminal state while the child was still alive and writing.
T6_PID=$(jq -r .child_identity.pid "$ST" 2>/dev/null || echo "")
[[ -z "$T6_PID" || "$T6_PID" == "null" ]] && T6_PID=$(jq -r .pid "$PIDS" 2>/dev/null || echo "")
T6_PGID=$(jq -r .child_identity.pgid "$ST" 2>/dev/null || echo "")
echo "$T6_PID" > "$TD/t6-child.pid"   # sidecar record of the fused child PID
chk "T6 recorded child PID" "ok" "$([ -n "$T6_PID" ] && [ "$T6_PID" != "null" ] && echo ok || echo missing)"
if kill -0 "$T6_PID" 2>/dev/null; then chk "T6 rate-fused child gone" gone alive; else chk "T6 rate-fused child gone" gone gone; fi
# No process may remain in the fused child's process group (same-PGID sweep).
REMAIN=$( { ps -o pgid= -p "$T6_PID" 2>/dev/null || true; } | tr -d ' ')
if [[ -n "$T6_PGID" && "$T6_PGID" != "null" ]]; then
  REMAIN2=$( { pgrep -g "$T6_PGID" 2>/dev/null || true; } | tr -d ' \n')
else
  REMAIN2=""
fi
chk "T6 no same-PGID descendant alive" "" "${REMAIN}${REMAIN2}"

# ── Test 7: pid-store identity + external kill validation ──
echo "═══ T7: pid-store contains pid/pgid/session_id for identity check ═══"
RAW="$TD/raw-t7.json"; ST="$TD/state-t7.json"; PIDS="$TD/pids-t7.json"
mk_nap() { cat > "$TD/nap.py" <<'PY'
import time
time.sleep(2)
PY
}
mk_nap
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((10*1024*1024)) --pid-store "$PIDS" \
  --task-id sup-t7 --task-id-source test \
  -- "$PY" "$TD/nap.py" &
SUP_PID=$!
# Wait briefly for pid-store
for _ in $(seq 1 40); do [[ -s "$PIDS" ]] && break; sleep 0.05; done
sleep 0.3
# jq exits 0/1 on condition; capture the file content directly
HAS_PID=$(jq -e '.pid > 0' "$PIDS" >/dev/null 2>&1 && echo y || echo n)
HAS_PGID=$(jq -e '.pgid > 0' "$PIDS" >/dev/null 2>&1 && echo y || echo n)
HAS_SID=$(jq -e '.session_id > 0' "$PIDS" >/dev/null 2>&1 && echo y || echo n)
EXPECTED_PGID=$(jq -r .pgid "$PIDS" 2>/dev/null)
EXPECTED_PID=$(jq -r .pid "$PIDS" 2>/dev/null)
chk "T7 pid-store has pid" y "$HAS_PID"
chk "T7 pid-store has pgid" y "$HAS_PGID"
chk "T7 pid-store has session_id" y "$HAS_SID"
# Process group must be reachable via kill -0
PROC_PGID=$(ps -o pgid= -p "$EXPECTED_PID" 2>/dev/null | tr -d ' ')
chk "T7 actual pgid matches recorded" "$EXPECTED_PGID" "$PROC_PGID"
wait $SUP_PID 2>/dev/null || true

# ── Test 8: rate fuse disabled (default) does not trip ──
echo "═══ T8: rate fuse disabled by default — burst producer is not killed by rate fuse ═══"
RAW="$TD/raw-t8.json"; ST="$TD/state-t8.json"; PIDS="$TD/pids-t8.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((50*1024*1024)) --pid-store "$PIDS" \
  --task-id sup-t8 --task-id-source test \
  -- "$PY" "$TD/bursts.py" >/dev/null 2>&1
set -e
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
REASON=$(jq -r .reason "$ST" 2>/dev/null || echo "")
chk "T8 status=reported (no rate fuse)" "reported" "$STATUS"
[[ "$REASON" != "rate_fuse"* ]] && chk "T8 reason != rate_fuse" y y || chk "T8 reason != rate_fuse" y n

# ── Test 9: escaped setsid descendant cannot push raw past the HARD cap ──
# The direct child forks a grandchild that setsid()-escapes into its own
# session, keeps the inherited raw fd, and keeps writing. Without a kernel
# RLIMIT_FSIZE this is the BLOCKER: raw grows past cap while state lies. With
# it, the file is bounded at raw_cap regardless of the escaped writer.
echo "═══ T9: escaped setsid descendant is bounded by kernel RLIMIT_FSIZE ═══"
CAP9=$((1024*1024))            # 1 MiB, mirrors the independent repro
T9SIDE="$TD/t9-grandchild.txt" # sidecar: grandchild pid + :done sentinel
cat > "$TD/escapee.py" <<'PY'
import os, sys, time
CAP_ATTEMPT = int(sys.argv[1])   # bytes to ATTEMPT (>> cap); kernel must bound
SIDE = sys.argv[2]
r, w = os.pipe()                 # grandchild -> parent "filled to cap" signal
pid = os.fork()
if pid > 0:
    # Direct child (the supervisor's tracked process). Wait until the escaped
    # grandchild has filled the file to the kernel cap, THEN exit — so the
    # grandchild's remaining writes happen strictly after the parent is gone.
    os.close(w)
    try:
        os.read(r, 1)
    except OSError:
        pass
    os.close(r)
    os._exit(0)
# Grandchild: escape into a brand-new session, keep the inherited stdout fd.
os.close(r)
os.setsid()
with open(SIDE, "w") as fh:
    fh.write(str(os.getpid()))
chunk = b"E" * (64 * 1024)
written = 0
while written < CAP_ATTEMPT:
    try:
        n = os.write(1, chunk)   # fd 1 == the supervisor's raw output file
    except OSError:
        break                    # EFBIG: RLIMIT_FSIZE reached → file at cap
    if not n:
        break
    written += n
os.write(w, b"x"); os.close(w)   # release the parent; it will now exit
# Prove we outlive the parent: wait for reparent, then try to write AGAIN.
for _ in range(100):
    try:
        if os.getppid() == 1:
            break
    except OSError:
        break
    time.sleep(0.02)
try:
    os.write(1, b"Z" * 65536)    # post-parent write; kernel cap must reject it
except OSError:
    pass
with open(SIDE, "a") as fh:
    fh.write(":done")
os._exit(0)
PY
RAW="$TD/raw-t9.json"; ST="$TD/state-t9.json"; PIDS="$TD/pids-t9.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap "$CAP9" --pid-store "$PIDS" \
  --task-id sup-t9 --task-id-source test \
  -- "$PY" "$TD/escapee.py" $((4*1024*1024)) "$T9SIDE" >/dev/null 2>&1
RC=$?
set -e
# Wait for the escaped grandchild to finish by itself; trap-kill as a safety net.
GPID=$( { sed 's/:done//' "$T9SIDE" 2>/dev/null || true; } | tr -d ' ')
trap 'set +e; [[ -n "${GPID:-}" ]] && kill -9 "$GPID" 2>/dev/null; if [[ -d "$TD" && "$P" == "0" && "$F" == "0" ]]; then rm -rf "$TD"; else if [[ -d "$TD" ]]; then cp -R "$TD" "$EVDIR"/testdir && echo "📂 preserved at $EVDIR/testdir"; fi; fi' EXIT
for _ in $(seq 1 100); do grep -q ":done" "$T9SIDE" 2>/dev/null && break; sleep 0.05; done
sleep 0.1
SIZE=$(stat -f %z "$RAW" 2>/dev/null || stat -c %s "$RAW" 2>/dev/null || echo 0)
RBYTES=$(jq -r .raw_bytes "$ST" 2>/dev/null || echo -1)
DIGEST=$(jq -r .raw_sha256 "$ST" 2>/dev/null || echo "")
ACT=$(shasum -a 256 "$RAW" 2>/dev/null | awk '{print $1}' || sha256sum "$RAW" | awk '{print $1}')
STATUS=$(jq -r .status "$ST" 2>/dev/null || echo unknown)
REASON=$(jq -r .reason "$ST" 2>/dev/null || echo "")
# HARD CAP: even with the escaped writer attempting 4 MiB, file never exceeds 1 MiB.
chk "T9 persisted raw <= hard cap" "ok" "$([ "$SIZE" -le "$CAP9" ] && echo ok || echo BREACH)"
chk "T9 state.raw_bytes == on-disk size" "$SIZE" "$RBYTES"
chk "T9 digest matches on-disk file" "$ACT" "$DIGEST"
chk "T9 supervisor exit=2 (cap tripped)" "2" "$RC"
chk "T9 status=resource_rejected" "resource_rejected" "$STATUS"
echo "$REASON" | grep -q "raw_cap" && chk "T9 reason mentions raw_cap" y y || chk "T9 reason mentions raw_cap" y n
# The escaped grandchild finished (post-parent write was kernel-rejected).
if [[ -n "$GPID" ]] && kill -0 "$GPID" 2>/dev/null; then chk "T9 escaped grandchild exited" gone alive; else chk "T9 escaped grandchild exited" gone gone; fi

# ── Test 10: truthful-containment branch proven deterministically ──
# The unreaped-direct-child path is (by POSIX) not reachable with a real child
# we own, so prove the code branch with a narrow pure-function unit fixture:
# containment_reason() must stamp child_not_reaped and must NOT imply clean
# containment when the child was not confirmed dead.
echo "═══ T10: containment_reason() marks unreaped child truthfully ═══"
T10=$("$PY" - "$SUP" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("supv", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
reaped = m.containment_reason("rate_fuse:x", reaped=True)
unreaped = m.containment_reason("rate_fuse:x", reaped=False)
empty = m.containment_reason("", reaped=False)
idem = m.containment_reason(unreaped, reaped=False)
ok = (
    reaped == "rate_fuse:x"
    and "child_not_reaped" in unreaped and "rate_fuse:x" in unreaped
    and "containment_failure" in unreaped
    and unreaped.count("child_not_reaped") == 1
    and idem.count("child_not_reaped") == 1
    and "child_not_reaped" in empty
)
print("ok" if ok else "bad")
PY
)
chk "T10 containment_reason branch truthful" "ok" "$T10"

# ─────────────────────────────────────────────────────────────────
# S1A: pure JSONL classifier (scripts/omp_stream_classifier.py)
# 纯函数分类器：不烧 token、不接运行时。用 importlib 装载模块跑断言，
# 每组打印单个 ok/bad token 供 chk 比对。CANARY 值贯穿源字段，验证
# verdict 与 diagnostic 均不泄漏原文/工具/provider 内容。
# ─────────────────────────────────────────────────────────────────
CLS="$ROOT/scripts/omp_stream_classifier.py"
echo "═══ S1A: omp_stream_classifier pure JSONL classifier ═══"
"$PY" -m py_compile "$CLS" 2>&1 | head -5
chk "S1A module compiles" "0" "$?"

# ── S1A-a: message_end preserves only assistant text blocks, strips canaries ──
S1A_A=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json, hashlib
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
CANARY = "CANARY_LEAK_9f3a"
rec = {
    "type": "message_end",
    "message": {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "hello"},
            {"type": "thinking", "text": "SECRET_" + CANARY},
            {"type": "tool_use", "name": "bash", "input": {"k": CANARY}},
            {"type": "text", "text": "world"},
            {"type": "text"},          # missing text -> dropped
            "notadict",                # non-dict block -> dropped
        ],
        "extra_field": CANARY,
        "usage": {"input_tokens": 10, "model": "m-" + CANARY},
    },
    "provider": "prov-" + CANARY,
    "model": "model-" + CANARY,
    "usage": {"tokens": 123, "leak": CANARY},
}
line = (json.dumps(rec) + "\n").encode()
r = f(line, 7)
ok = r.decision == "preserve"
vt = r.verdict_line
ok = ok and vt is not None and vt.endswith(b"\n")
ok = ok and json.loads(vt.decode()) == {
    "type": "message_end",
    "message": {"role": "assistant", "content": [
        {"type": "text", "text": "hello"},
        {"type": "text", "text": "world"},
    ]},
}
# canary must not leak into verdict bytes nor diagnostic
ok = ok and CANARY.encode() not in vt
ok = ok and CANARY not in json.dumps(r.diagnostic_record)
dg = r.diagnostic_record
ok = ok and dg["input_sha256"] == hashlib.sha256(line).hexdigest()
ok = ok and dg["input_bytes"] == len(line) and dg["seq"] == 7
ok = ok and dg["type"] == "message_end" and dg["decision"] == "preserve"
# determinism: identical bytes for identical input
ok = ok and f(line, 7).verdict_line == vt
# canonical: sorted keys -> top-level "message" precedes "type"
ok = ok and vt.startswith(b'{"message":')
print("ok" if ok else "bad")
PY
)
chk "S1A-a message_end preserve+canary-strip+canonical" "ok" "$S1A_A"

# ── S1A-b: message_update text_delta and top-level text_delta canonicalize ──
S1A_B=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
CANARY = "CANARY_LEAK_9f3a"
mu = {"type": "message_update",
      "assistantMessageEvent": {"type": "text_delta", "text": "hi", "index": 3, "leak": CANARY},
      "seq": 1, "other": CANARY}
r = f((json.dumps(mu) + "\n").encode(), 1)
ok = r.decision == "preserve"
ok = ok and json.loads(r.verdict_line.decode()) == {
    "type": "message_update",
    "assistantMessageEvent": {"type": "text_delta", "delta": "hi"}}
ok = ok and CANARY.encode() not in r.verdict_line
# top-level text_delta
td = {"type": "text_delta", "text": "abc", "provider": CANARY}
r = f((json.dumps(td) + "\n").encode(), 2)
ok = ok and r.decision == "preserve"
ok = ok and json.loads(r.verdict_line.decode()) == {"type": "text_delta", "text": "abc"}
ok = ok and CANARY.encode() not in r.verdict_line
# message_update with non-string delta/text -> unknown + terminal-capable
mu2 = {"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": 123}}
r = f((json.dumps(mu2) + "\n").encode(), 3)
ok = ok and r.decision == "unknown" and r.verdict_line is None and r.terminal_capable is True
print("ok" if ok else "bad")
PY
)
chk "S1A-b text_delta canonicalization" "ok" "$S1A_B"

# ── S1A-c: turn_end preserves only stopReason (string / null / missing) ──
S1A_C=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
CANARY = "CANARY_LEAK_9f3a"
te = {"type": "turn_end", "message": {"stopReason": "end_turn", "tokens": 5, "leak": CANARY}}
r = f((json.dumps(te) + "\n").encode(), 1)
ok = r.decision == "preserve"
ok = ok and json.loads(r.verdict_line.decode()) == {"type": "turn_end", "message": {"stopReason": "end_turn"}}
ok = ok and CANARY.encode() not in r.verdict_line
# missing stopReason -> null
r = f((json.dumps({"type": "turn_end", "message": {"foo": 1}}) + "\n").encode(), 2)
ok = ok and json.loads(r.verdict_line.decode()) == {"type": "turn_end", "message": {"stopReason": None}}
# explicit null stopReason -> null
r = f((json.dumps({"type": "turn_end", "message": {"stopReason": None}}) + "\n").encode(), 3)
ok = ok and json.loads(r.verdict_line.decode()) == {"type": "turn_end", "message": {"stopReason": None}}
# non-string stopReason canonicalizes to null
r = f((json.dumps({"type": "turn_end", "message": {"stopReason": 42}}) + "\n").encode(), 4)
ok = ok and json.loads(r.verdict_line.decode()) == {"type": "turn_end", "message": {"stopReason": None}}
# message not an object -> unknown
r = f((json.dumps({"type": "turn_end", "message": "x"}) + "\n").encode(), 5)
ok = ok and r.decision == "unknown" and r.verdict_line is None
print("ok" if ok else "bad")
PY
)
chk "S1A-c turn_end stopReason-only" "ok" "$S1A_C"

# ── S1A-d: thinking/toolcall + protocol envelopes deny; diagnostic has no canaries ──
S1A_D=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
CANARY = "CANARY_LEAK_9f3a"
KEYSET = {"seq", "type", "subtype", "input_bytes", "input_sha256", "decision", "reason", "terminal_capable", "structure_code"}
ok = True
denies = [
    {"type": "message_update", "assistantMessageEvent": {"type": "thinking_delta", "text": "SECRET" + CANARY}},
    {"type": "message_update", "assistantMessageEvent": {"type": "toolcall_delta", "arguments": CANARY}},
    {"type": "session", "id": CANARY},
    {"type": "ready"},
    {"type": "agent_start"},
    {"type": "turn_start"},
    {"type": "message_start", "message": {"role": "assistant"}},
    {"type": "tool_execution_start", "tool": "bash", "input": CANARY},
    {"type": "tool_execution_end", "output": CANARY},
    {"type": "usage", "tokens": 9, "leak": CANARY},
    {"type": "heartbeat"},
]
for env in denies:
    r = f((json.dumps(env) + "\n").encode(), 1)
    if r.decision != "deny" or r.verdict_line is not None:
        ok = False
    if CANARY in json.dumps(r.diagnostic_record):
        ok = False
    if set(r.diagnostic_record.keys()) != KEYSET:
        ok = False
print("ok" if ok else "bad")
PY
)
chk "S1A-d deny envelopes, no canary in diagnostic" "ok" "$S1A_D"

# ── S1A-e: malformed inputs -> unknown, no verdict; 1 MiB inclusive boundary allowed ──
S1A_E=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json, hashlib
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
ok = True
# invalid UTF-8
r = f(b"\xff\xfe\x00\n", 1); ok = ok and r.decision == "unknown" and r.verdict_line is None
# no trailing newline
r = f(b'{"type":"text_delta","text":"x"}', 2); ok = ok and r.decision == "unknown" and r.verdict_line is None
# non-object: array / bare string
r = f(b"[1,2,3]\n", 3); ok = ok and r.decision == "unknown" and r.verdict_line is None
r = f(b'"astring"\n', 4); ok = ok and r.decision == "unknown"
# JSON failure
r = f(b"{bad json\n", 5); ok = ok and r.decision == "unknown"
# oversize > 1 MiB (otherwise valid) -> unknown by size
big = b'{"type":"text_delta","text":"' + b"a" * (1024 * 1024) + b'"}\n'
r = f(big, 6); ok = ok and r.decision == "unknown" and r.verdict_line is None
# hash still computed for malformed input bytes
r = f(b"\xff\n", 7); ok = ok and r.diagnostic_record["input_sha256"] == hashlib.sha256(b"\xff\n").hexdigest()
# exactly 1 MiB inclusive is NOT rejected for size -> still classifies (preserve)
base = '{"type":"text_delta","text":"' + '"}'
pad = 1024 * 1024 - len(base.encode()) - 1  # -1 for trailing newline
line = ('{"type":"text_delta","text":"' + "a" * pad + '"}\n').encode()
assert len(line) == 1024 * 1024
r = f(line, 8); ok = ok and r.decision == "preserve" and r.verdict_line is not None
print("ok" if ok else "bad")
PY
)
chk "S1A-e malformed=>unknown, 1MiB boundary ok" "ok" "$S1A_E"

# ── S1A-f: terminal-capable unknown vs harmless unknown (structural, not scalar text) ──
S1A_F=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
ok = True
# nested terminal key -> terminal-capable
u1 = {"type": "weird_envelope", "payload": {"deep": [{"required_actions": []}]}}
r = f((json.dumps(u1) + "\n").encode(), 1)
ok = ok and r.decision == "unknown" and r.terminal_capable is True
# no terminal keys -> harmless
u2 = {"type": "weird", "foo": 1, "bar": [1, 2, {"baz": "qux"}]}
r = f((json.dumps(u2) + "\n").encode(), 2)
ok = ok and r.decision == "unknown" and r.terminal_capable is False
# scalar string mentioning terminal words must NOT count
u3 = {"type": "weird", "note": "this mentions severity and evidence and required_actions words"}
r = f((json.dumps(u3) + "\n").encode(), 3)
ok = ok and r.decision == "unknown" and r.terminal_capable is False
print("ok" if ok else "bad")
PY
)
chk "S1A-f terminal-capable vs harmless unknown" "ok" "$S1A_F"

# ── S1A-g: exact diagnostic key set + deterministic verdict bytes ──
S1A_G=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
KEYSET = {"seq", "type", "subtype", "input_bytes", "input_sha256", "decision", "reason", "terminal_capable", "structure_code"}
line = b'{"type":"text_delta","text":"z"}\n'
r = f(line, 5)
ok = set(r.diagnostic_record.keys()) == KEYSET
ok = ok and r.terminal_capable == r.diagnostic_record["terminal_capable"]
ok = ok and r.verdict_line == f(line, 5).verdict_line  # deterministic
# malformed record also carries the exact key set
r2 = f(b"nope\n", 9)
ok = ok and set(r2.diagnostic_record.keys()) == KEYSET
print("ok" if ok else "bad")
PY
)
chk "S1A-g exact diagnostic keys + determinism" "ok" "$S1A_G"

# ── S1A-h: structural purity — no filesystem/env/subprocess/open in the module ──
# Strip Python comments (# .. EOL) first so prose in the header banner cannot
# trip the check; assert on executable code only.
if sed 's/#.*$//' "$CLS" | grep -Eq 'import[[:space:]]+os([[:space:]]|$|,)|from[[:space:]]+os[[:space:]]|import[[:space:]]+pathlib|from[[:space:]]+pathlib|import[[:space:]]+subprocess|from[[:space:]]+subprocess|(^|[^.[:alnum:]_])open[[:space:]]*\(|environ'; then
  chk "S1A-h no os/pathlib/subprocess/open/environ" "clean" "dirty"
else
  chk "S1A-h no os/pathlib/subprocess/open/environ" "clean" "clean"
fi

# ── S1A-i (return1/M1): unpaired surrogate scalar => unknown, no verdict, no throw ──
# Three surface locations: top-level text_delta, message_end assistant text block,
# message_update.text_delta. Each must return unknown with no verdict and must not
# raise (a throw would abort the driver and fail the token comparison).
S1A_I=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
# Raw bytes carry the escaped lone surrogate; json.loads yields a lone-surrogate str.
cases = [
    b'{"type":"text_delta","text":"\\ud800"}\n',
    b'{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"\\udc00"}]}}\n',
    b'{"type":"message_update","assistantMessageEvent":{"type":"text_delta","text":"\\ud83d"}}\n',
]
ok = True
for i, line in enumerate(cases, 1):
    try:
        r = f(line, i)
    except Exception:
        ok = False
        break
    if r.decision != "unknown" or r.verdict_line is not None:
        ok = False
    if r.diagnostic_record["reason"] != "invalid_unicode_scalar":
        ok = False
    if r.diagnostic_record["decision"] != "unknown":
        ok = False
print("ok" if ok else "bad")
PY
)
chk "S1A-i surrogate scalars => unknown, no throw" "ok" "$S1A_I"

# ── S1A-j (return1/M2): unknown top-level type canary must not leak into diagnostic ──
S1A_J=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
r = f(b'{"type":"CANARY_TYPE_PRIVATE","foo":1}\n', 1)
ok = r.decision == "unknown"
ok = ok and r.diagnostic_record["type"] is None
ok = ok and "CANARY_TYPE_PRIVATE" not in json.dumps(r.diagnostic_record)
print("ok" if ok else "bad")
PY
)
chk "S1A-j unknown type canary -> type=null, no leak" "ok" "$S1A_J"

# ── S1A-k (return1/M2): unknown message_update subtype canary must not leak ──
S1A_K=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
r = f(b'{"type":"message_update","assistantMessageEvent":{"type":"CANARY_SUB_PRIVATE"}}\n', 1)
ok = r.decision == "unknown"
ok = ok and r.diagnostic_record["subtype"] is None
ok = ok and r.diagnostic_record["type"] == "message_update"   # recognized safe enum retained
ok = ok and "CANARY_SUB_PRIVATE" not in json.dumps(r.diagnostic_record)
# recognized reasoning subtype normalizes to a fixed safe code (not the raw string)
r2 = f(b'{"type":"message_update","assistantMessageEvent":{"type":"toolcall_CANARY_SUB_PRIVATE"}}\n', 2)
ok = ok and r2.decision == "deny" and r2.diagnostic_record["subtype"] == "reasoning_stream"
ok = ok and "CANARY_SUB_PRIVATE" not in json.dumps(r2.diagnostic_record)
print("ok" if ok else "bad")
PY
)
chk "S1A-k unknown subtype canary -> subtype=null, no leak" "ok" "$S1A_K"

# ── S3A-a: structure_code — every message_end / message_update branch gets its
#    fixed allowlist code; decisions/terminal/reason semantics unchanged. ──
S3A_A=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
def sc(rec):
    r = f((json.dumps(rec) + "\n").encode(), 1)
    return r.decision, r.diagnostic_record["structure_code"], r.diagnostic_record["reason"]
ok = True
# message_end branches
ok = ok and sc({"type": "message_end", "message": {"role": "assistant", "content": []}}) == (
    "preserve", "message_end.assistant", "message_end.assistant")
# S3B: message object with role != assistant is now a DENY (known non-verdict envelope)
ok = ok and sc({"type": "message_end", "message": {"role": "user", "content": []}}) == (
    "deny", "message_end.non_assistant", "message_end.non_assistant")
# role missing is still a dict -> non_assistant -> deny
ok = ok and sc({"type": "message_end", "message": {"content": []}}) == (
    "deny", "message_end.non_assistant", "message_end.non_assistant")
# message key absent -> message_missing (reason still the legacy aggregate key)
ok = ok and sc({"type": "message_end"}) == (
    "unknown", "message_end.message_missing", "message_end.non_assistant")
# explicit null message -> message_missing
ok = ok and sc({"type": "message_end", "message": None}) == (
    "unknown", "message_end.message_missing", "message_end.non_assistant")
# non-object message -> message_non_object
ok = ok and sc({"type": "message_end", "message": "x"}) == (
    "unknown", "message_end.message_non_object", "message_end.non_assistant")
ok = ok and sc({"type": "message_end", "message": [1, 2]}) == (
    "unknown", "message_end.message_non_object", "message_end.non_assistant")
# message_update branches
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "text": "hi"}}) == (
    "preserve", "message_update.text_delta", "message_update.text_delta")
# text_delta shape but no string delta -> still text_delta structure, unknown decision
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": 5}}) == (
    "unknown", "message_update.text_delta", "message_update.text_delta.no_string_delta")
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "thinking_delta"}}) == (
    "deny", "message_update.reasoning_stream", "message_update.reasoning_stream")
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "toolcall_delta"}}) == (
    "deny", "message_update.reasoning_stream", "message_update.reasoning_stream")
# ame is dict but unrecognized kind
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "mystery"}}) == (
    "unknown", "message_update.ame_unknown_kind", "message_update.unrecognized")
# ame absent -> ame_missing
ok = ok and sc({"type": "message_update"}) == (
    "unknown", "message_update.ame_missing", "message_update.unrecognized")
ok = ok and sc({"type": "message_update", "assistantMessageEvent": None}) == (
    "unknown", "message_update.ame_missing", "message_update.unrecognized")
# ame non-object -> ame_non_object
ok = ok and sc({"type": "message_update", "assistantMessageEvent": "x"}) == (
    "unknown", "message_update.ame_non_object", "message_update.unrecognized")
# unrelated envelopes -> structure_code null
for env in (
    {"type": "text_delta", "text": "abc"},
    {"type": "turn_end", "message": {"stopReason": "stop"}},
    {"type": "session", "id": "s"},
    {"type": "heartbeat"},
    {"type": "totally_unknown", "foo": 1},
):
    r = f((json.dumps(env) + "\n").encode(), 1)
    ok = ok and r.diagnostic_record["structure_code"] is None
# malformed inputs -> null
for line in (b"nope\n", b"[1,2]\n", b'{"type":"text_delta","text":"x"}'):
    ok = ok and f(line, 1).diagnostic_record["structure_code"] is None
# every emitted structure_code is drawn only from the module allowlist
print("ok" if ok else "bad")
PY
)
chk "S3A-a structure_code per-branch mapping + null for unrelated" "ok" "$S3A_A"

# ── S3A-b: arbitrary role/type/subtype canary must NEVER enter structure_code
#    (nor any diagnostic field); code is always an allowlist literal. ──
S3A_B=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
CANARY = "CANARY_STRUCT_PRIVATE_5c1a"
ok = True
cases = [
    {"type": "message_end", "message": {"role": CANARY, "content": []}},
    {"type": "message_end", "message": {"role": "assistant", "content": [
        {"type": CANARY, "text": CANARY}]}},
    {"type": "message_end", "message": CANARY},
    {"type": "message_update", "assistantMessageEvent": {"type": CANARY}},
    {"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "text": CANARY}},
    {"type": "message_update", "assistantMessageEvent": CANARY},
    {"type": CANARY, "assistantMessageEvent": {"type": CANARY}},
]
for env in cases:
    r = f((json.dumps(env) + "\n").encode(), 1)
    dg = r.diagnostic_record
    code = dg["structure_code"]
    # structure_code is either None or a fixed allowlist literal — never source text
    if code is not None and code not in m.STRUCTURE_CODES:
        ok = False
    if CANARY in json.dumps(dg):
        ok = False
# defensive: _diag refuses any non-allowlist value, coercing to None
if m._diag(1, None, None, 0, "h", "unknown", "r", False, CANARY)["structure_code"] is not None:
    ok = False
if m._diag(1, None, None, 0, "h", "unknown", "r", False, "message_end.assistant")["structure_code"] != "message_end.assistant":
    ok = False
print("ok" if ok else "bad")
PY
)
chk "S3A-b role/type/subtype canary never enters structure_code" "ok" "$S3A_B"

# ── S3A-c: deterministic keyset now includes structure_code across all paths;
#    canonical serialization stable. ──
S3A_C=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
KEYSET = {"seq", "type", "subtype", "input_bytes", "input_sha256", "decision", "reason", "terminal_capable", "structure_code"}
ok = m.DIAGNOSTIC_KEYS == KEYSET
lines = [
    b'{"type":"message_end","message":{"role":"assistant","content":[]}}\n',
    b'{"type":"message_end"}\n',
    b'{"type":"message_update","assistantMessageEvent":{"type":"text_delta","text":"a"}}\n',
    b'{"type":"session"}\n',
    b'nope\n',
]
for ln in lines:
    r = f(ln, 3)
    ok = ok and set(r.diagnostic_record.keys()) == KEYSET
    ok = ok and r.diagnostic_record == f(ln, 3).diagnostic_record  # deterministic
print("ok" if ok else "bad")
PY
)
chk "S3A-c diagnostic keyset includes structure_code, deterministic" "ok" "$S3A_C"

# ── S3B-a: non-assistant message_end is DENY (known non-verdict envelope), not
#    unknown; no verdict line; terminal boolean retained but never a
#    terminal-unknown; assistant/missing/non-object decisions unchanged; the
#    non-assistant role string never leaks into verdict or diagnostic. ──
S3B_A=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
CANARY = "CANARY_ROLE_PRIVATE_3d7b"
ok = True
# message object with role != assistant -> deny, no verdict.
for role in ("user", "system", "tool", "Assistant", CANARY, "", "assistant_impostor"):
    r = f((json.dumps({"type": "message_end",
                       "message": {"role": role, "content": [{"type": "text", "text": CANARY}]}}) + "\n").encode(), 1)
    ok = ok and r.decision == "deny"
    ok = ok and r.verdict_line is None
    # structure_code is the fixed allowlist literal; decision is not unknown so this
    # never contributes to the terminal-capable-unknown count even though "message"
    # is a terminal-shaped key (terminal_capable may be True).
    ok = ok and r.diagnostic_record["structure_code"] == "message_end.non_assistant"
    ok = ok and r.diagnostic_record["decision"] == "deny"
    ok = ok and r.diagnostic_record["terminal_capable"] == r.terminal_capable
    # no canary / role text anywhere in verdict (there is none) or diagnostic.
    ok = ok and CANARY not in json.dumps(r.diagnostic_record)
# role missing but message is a dict -> still non_assistant -> deny.
r = f(b'{"type":"message_end","message":{"content":[]}}\n', 1)
ok = ok and r.decision == "deny" and r.diagnostic_record["structure_code"] == "message_end.non_assistant"
# assistant path unchanged -> preserve.
r = f(b'{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"hi"}]}}\n', 1)
ok = ok and r.decision == "preserve" and r.verdict_line is not None
# message missing / null -> unchanged unknown (fail-closed), not deny.
for line in (b'{"type":"message_end"}\n', b'{"type":"message_end","message":null}\n'):
    r = f(line, 1)
    ok = ok and r.decision == "unknown" and r.verdict_line is None
    ok = ok and r.diagnostic_record["structure_code"] == "message_end.message_missing"
# message present but non-object -> unchanged unknown.
for line in (b'{"type":"message_end","message":"x"}\n', b'{"type":"message_end","message":[1,2]}\n'):
    r = f(line, 1)
    ok = ok and r.decision == "unknown" and r.verdict_line is None
    ok = ok and r.diagnostic_record["structure_code"] == "message_end.message_non_object"
# message_update unrecognized kind stays unknown/fail-closed (NOT broadened to deny).
r = f(b'{"type":"message_update","assistantMessageEvent":{"type":"mystery"}}\n', 1)
ok = ok and r.decision == "unknown" and r.diagnostic_record["structure_code"] == "message_update.ame_unknown_kind"
print("ok" if ok else "bad")
PY
)
chk "S3B-a non-assistant message_end => deny, others unchanged, no leak" "ok" "$S3B_A"

# ── S3C-a: message_update unknown-kind gains fixed structural sub-codes for the
#    potential verdict-bearing shapes (string delta / string text / stopReason);
#    a non-verdict-bearing (inert) unknown-kind stays the base code; the decision,
#    reason and terminal_capable semantics are all unchanged (additive-only). ──
S3C_A=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
def sc(rec):
    r = f((json.dumps(rec) + "\n").encode(), 1)
    return r.decision, r.diagnostic_record["structure_code"], r.diagnostic_record["reason"]
ok = True
# unknown kind + string delta -> delta_string (a possibly-renamed text_delta shape)
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "newkind", "delta": "hi"}}) == (
    "unknown", "message_update.ame_unknown_kind.delta_string", "message_update.unrecognized")
# type missing entirely but string delta present -> still delta_string
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"delta": "hi"}}) == (
    "unknown", "message_update.ame_unknown_kind.delta_string", "message_update.unrecognized")
# unknown kind + string text (no string delta) -> text_string
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "newkind", "text": "hi"}}) == (
    "unknown", "message_update.ame_unknown_kind.text_string", "message_update.unrecognized")
# string delta wins over string text
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "x", "delta": "d", "text": "t"}}) == (
    "unknown", "message_update.ame_unknown_kind.delta_string", "message_update.unrecognized")
# unknown kind + stopReason present (any type: string or null) -> stop_reason
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "x", "stopReason": "stop"}}) == (
    "unknown", "message_update.ame_unknown_kind.stop_reason", "message_update.unrecognized")
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "x", "stopReason": None}}) == (
    "unknown", "message_update.ame_unknown_kind.stop_reason", "message_update.unrecognized")
# non-string delta/text carries no verdict text -> falls back to the inert base code
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "x", "delta": 5}}) == (
    "unknown", "message_update.ame_unknown_kind", "message_update.unrecognized")
# truly inert unknown kind -> unchanged base code (backward compatible with S3A/S3B)
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "mystery"}}) == (
    "unknown", "message_update.ame_unknown_kind", "message_update.unrecognized")
# recognized kinds are untouched by the refinement
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "text": "hi"}}) == (
    "preserve", "message_update.text_delta", "message_update.text_delta")
ok = ok and sc({"type": "message_update", "assistantMessageEvent": {"type": "thinking_delta"}}) == (
    "deny", "message_update.reasoning_stream", "message_update.reasoning_stream")
# terminal_capable unchanged: delta is a terminal key -> True regardless of the sub-code
r = f(b'{"type":"message_update","assistantMessageEvent":{"type":"x","delta":"d"}}\n', 1)
ok = ok and r.terminal_capable is True and r.diagnostic_record["terminal_capable"] is True
print("ok" if ok else "bad")
PY
)
chk "S3C-a message_update unknown-kind verdict-shape sub-codes" "ok" "$S3C_A"

# ── S3C-b: unclassified (unrecognized top-level type) gains fixed structural
#    sub-codes for potential verdict-bearing shapes; an inert unclassified
#    envelope keeps structure_code=null; decision/reason stay unknown/"unclassified". ──
S3C_B=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
def sc(rec):
    r = f((json.dumps(rec) + "\n").encode(), 1)
    return r.decision, r.diagnostic_record["structure_code"], r.diagnostic_record["reason"]
ok = True
# assistantMessageEvent hanging off an unknown top-level type -> assistant_message_event
ok = ok and sc({"type": "weird", "assistantMessageEvent": {"type": "text_delta", "delta": "x"}}) == (
    "unknown", "unclassified.assistant_message_event", "unclassified")
# type key missing entirely but aME present -> assistant_message_event
ok = ok and sc({"assistantMessageEvent": {"type": "text_delta"}}) == (
    "unknown", "unclassified.assistant_message_event", "unclassified")
# message present under unknown type -> message (message_end / turn_end form)
ok = ok and sc({"type": "weird", "message": {"role": "assistant", "content": []}}) == (
    "unknown", "unclassified.message", "unclassified")
# aME takes priority over message when both are present
ok = ok and sc({"type": "weird", "assistantMessageEvent": {}, "message": {}}) == (
    "unknown", "unclassified.assistant_message_event", "unclassified")
# direct string delta / text / stopReason at the top level
ok = ok and sc({"type": "weird", "delta": "x"}) == (
    "unknown", "unclassified.delta_string", "unclassified")
ok = ok and sc({"type": "weird", "text": "x"}) == (
    "unknown", "unclassified.text_string", "unclassified")
ok = ok and sc({"type": "weird", "stopReason": "stop"}) == (
    "unknown", "unclassified.stop_reason", "unclassified")
# inert unclassified -> structure_code stays null (backward compatible with S3A-a)
ok = ok and sc({"type": "totally_unknown", "foo": 1}) == ("unknown", None, "unclassified")
# type missing + inert -> null
ok = ok and sc({"foo": 1, "bar": [1, 2]}) == ("unknown", None, "unclassified")
# non-string delta/text at top level is not verdict-bearing -> null (inert)
ok = ok and sc({"type": "weird", "delta": 5, "text": 9}) == ("unknown", None, "unclassified")
print("ok" if ok else "bad")
PY
)
chk "S3C-b unclassified verdict-shape sub-codes + inert stays null" "ok" "$S3C_B"

# ── S3C-c: every new verdict-shape sub-code is a fixed allowlist literal — no
#    source value (role/type/subtype/body) can ever enter structure_code; every
#    emitted code is drawn from m.STRUCTURE_CODES; _diag still coerces any
#    non-allowlist value to null. ──
S3C_C=$("$PY" - "$CLS" <<'PY'
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("cls", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = m.classify_jsonl_line
CANARY = "CANARY_S3C_PRIVATE_1b9d"
ok = True
cases = [
    # canary as the ame kind AND as content values under an unknown kind
    {"type": "message_update", "assistantMessageEvent": {"type": CANARY, "delta": CANARY}},
    {"type": "message_update", "assistantMessageEvent": {"type": CANARY, "text": CANARY}},
    {"type": "message_update", "assistantMessageEvent": {"type": CANARY, "stopReason": CANARY}},
    # canary as an unknown top-level type AND as content values
    {"type": CANARY, "assistantMessageEvent": {"type": CANARY, "delta": CANARY}},
    {"type": CANARY, "message": {"role": CANARY, "content": [{"type": CANARY, "text": CANARY}]}},
    {"type": CANARY, "delta": CANARY},
    {"type": CANARY, "text": CANARY},
    {"type": CANARY, "stopReason": CANARY},
]
for env in cases:
    r = f((json.dumps(env) + "\n").encode(), 1)
    dg = r.diagnostic_record
    code = dg["structure_code"]
    # structure_code is either None or a fixed allowlist literal — never source text
    if code is not None and code not in m.STRUCTURE_CODES:
        ok = False
    if CANARY in json.dumps(dg):
        ok = False
    # deterministic across identical bytes
    if f((json.dumps(env) + "\n").encode(), 1).diagnostic_record != dg:
        ok = False
# all eight new S3C sub-codes must be present in the module allowlist
for c in (
    "message_update.ame_unknown_kind.delta_string",
    "message_update.ame_unknown_kind.text_string",
    "message_update.ame_unknown_kind.stop_reason",
    "unclassified.assistant_message_event",
    "unclassified.message",
    "unclassified.delta_string",
    "unclassified.text_string",
    "unclassified.stop_reason",
):
    if c not in m.STRUCTURE_CODES:
        ok = False
# defensive: _diag coerces any non-allowlist (canary-derived) value to None
if m._diag(1, None, None, 0, "h", "unknown", "r", False, "unclassified." + CANARY)["structure_code"] is not None:
    ok = False
if m._diag(1, None, None, 0, "h", "unknown", "r", False, "unclassified.message")["structure_code"] != "unclassified.message":
    ok = False
print("ok" if ok else "bad")
PY
)
chk "S3C-c verdict-shape codes are allowlist-only, canary never leaks" "ok" "$S3C_C"

# ── S3B-b: supervisor accepts a stream carrying a non-assistant message_end
#    (now a deny) followed by a valid verdict → reported, not resource_rejected;
#    the deny is counted, contributes zero terminal-unknown, and its role string
#    never reaches the sanitized raw / diagnostic / state. ──
echo "── S3B-b: non-assistant message_end deny does not poison capture ──"
MIB=$((1024*1024)); KIB=1024
S3B_CANARY="CANARY_ROLE_SUP_9a4e"
cat > "$TD/prodS3B.py" <<PY
import sys
C = "$S3B_CANARY"
w = sys.stdout.write
w('{"type":"message_end","message":{"role":"user","content":[{"type":"text","text":"' + C + '"}]}}\n')  # non-assistant -> deny
w('{"type":"text_delta","text":"visible verdict body"}\n')
w('{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"final clean"}]}}\n')
w('{"type":"turn_end","message":{"stopReason":"stop"}}\n')
sys.stdout.flush()
PY
RAW="$TD/raw-s3b.json"; ST="$TD/state-s3b.json"; PIDS="$TD/pids-s3b.json"; DIAG="$RAW.diag.jsonl"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) \
  --verdict-cap $((1*MIB)) --diagnostic-cap $((512*KIB)) \
  --task-id sup-s3b --task-id-source test \
  -- "$PY" "$TD/prodS3B.py" >/dev/null 2>&1
RC=$?
set -e
chk "S3B-b status=reported" "reported" "$(jq -r .status "$ST")"
chk "S3B-b supervisor exit=0" "0" "$RC"
chk "S3B-b denied_count>=1" "ok" "$([ "$(jq -r .denied_count "$ST")" -ge 1 ] && echo ok || echo no)"
chk "S3B-b terminal_capable_unknown_count=0" "0" "$(jq -r .terminal_capable_unknown_count "$ST")"
chk "S3B-b unknown_count=0" "0" "$(jq -r .unknown_count "$ST")"
# preserved = text_delta + assistant message_end + turn_end = 3
chk "S3B-b preserved_count=3" "3" "$(jq -r .preserved_count "$ST")"
# the non-assistant role's canary text must never reach sanitized raw / diag / state
chk "S3B-b no canary in raw"  "0" "$(grep -c "$S3B_CANARY" "$RAW"  2>/dev/null; true)"
chk "S3B-b no canary in diag" "0" "$(grep -c "$S3B_CANARY" "$DIAG" 2>/dev/null; true)"
chk "S3B-b no canary in state" "0" "$(grep -c "$S3B_CANARY" "$ST" 2>/dev/null; true)"
# the denied non-assistant message_end produced no verdict line in raw
chk "S3B-b raw has no user role" "0" "$(grep -c '"role":"user"' "$RAW" 2>/dev/null; true)"

# ─────────────────────────────────────────────────────────────────
# S1B: opt-in verdict_v1 pipe capture in supervisor
# 只有 --capture-mode verdict_v1 走管道分帧 + 分类落规范 verdict；legacy 不变。
# 不烧 token、不接真 OMP：用 python 生产者 mock stdout 流。
# ─────────────────────────────────────────────────────────────────
echo "═══ S1B: verdict_v1 pipe capture ═══"
sha() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" | awk '{print $1}'; }
sz()  { stat -f %z "$1" 2>/dev/null || stat -c %s "$1" 2>/dev/null || echo 0; }
MIB=$((1024*1024)); KIB=1024
CANARY="CANARY_LEAK_S1B_7e2f"

# 生产者 A：>25 MiB thinking_delta（deny，含 canary）+ 合法 text_delta / message_end
# （含 thinking/tool/provider/usage canary，均应被剥离）/ turn_end(stop)。
cat > "$TD/prodA.py" <<PY
import sys
C = "$CANARY"
think = "T" * 8192
tline = '{"type":"message_update","assistantMessageEvent":{"type":"thinking_delta","text":"' + C + think + '"}}\n'
w = sys.stdout.write
for _ in range(3400):            # ~28 MiB ingress
    w(tline)
w('{"type":"message_update","assistantMessageEvent":{"type":"text_delta","text":"visible answer no secrets"}}\n')
w('{"type":"message_end","message":{"role":"assistant","content":['
  '{"type":"text","text":"final clean text"},'
  '{"type":"thinking","text":"' + C + '"},'
  '{"type":"tool_use","name":"bash","input":{"cmd":"' + C + '"}}'
  ']},"provider":"prov-' + C + '","usage":{"leak":"' + C + '"}}\n')
w('{"type":"turn_end","message":{"stopReason":"stop"}}\n')
sys.stdout.flush()
PY

# ── S1B-1: big thinking stream reported, verdict sanitized, diag truncated ──
echo "── S1B-1: >25MiB thinking + valid end → reported, sanitized, diag truncated ──"
RAW="$TD/raw-b1.json"; ST="$TD/state-b1.json"; PIDS="$TD/pids-b1.json"; DIAG="$RAW.diag.jsonl"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((40*MIB)) \
  --verdict-cap $((1*MIB)) --diagnostic-cap $((512*KIB)) \
  --task-id sup-b1 --task-id-source test \
  -- "$PY" "$TD/prodA.py" >/dev/null 2>&1
RC=$?
set -e
STATUS=$(jq -r .status "$ST"); ING=$(jq -r .ingress_bytes "$ST")
RSZ=$(sz "$RAW"); DSZ=$(sz "$DIAG")
chk "B1 status=reported" "reported" "$STATUS"
chk "B1 supervisor exit=0" "0" "$RC"
chk "B1 capture_mode=verdict_v1" "verdict_v1" "$(jq -r .capture_mode "$ST")"
chk "B1 raw <= verdict cap" "ok" "$([ "$RSZ" -le $((1*MIB)) ] && echo ok || echo too_big)"
chk "B1 ingress > 20MiB" "ok" "$([ "$ING" -gt $((20*MIB)) ] && echo ok || echo small)"
chk "B1 diag <= diag cap" "ok" "$([ "$DSZ" -le $((512*KIB)) ] && echo ok || echo too_big)"
chk "B1 diagnostic_truncated=true" "true" "$(jq -r .diagnostic_truncated "$ST")"
chk "B1 raw has message_end" "y" "$(grep -q '"type":"message_end"' "$RAW" && echo y || echo n)"
chk "B1 raw has turn_end" "y" "$(grep -q '"type":"turn_end"' "$RAW" && echo y || echo n)"
chk "B1 raw has text_delta" "y" "$(grep -q '"type":"text_delta"' "$RAW" && echo y || echo n)"
# canary must not appear anywhere: raw, diag, or state
chk "B1 no canary in raw"  "0" "$(grep -c "$CANARY" "$RAW"  2>/dev/null; true)"
chk "B1 no canary in diag" "0" "$(grep -c "$CANARY" "$DIAG" 2>/dev/null; true)"
chk "B1 no canary in state" "0" "$(grep -c "$CANARY" "$ST" 2>/dev/null; true)"
# no thinking/tool substrings leaked into raw
chk "B1 no thinking payload in raw" "0" "$(grep -c 'TTTT' "$RAW" 2>/dev/null; true)"
# state digests match the real files
chk "B1 raw_bytes == on-disk"   "$RSZ" "$(jq -r .raw_bytes "$ST")"
chk "B1 raw_sha256 == file"      "$(sha "$RAW")"  "$(jq -r .raw_sha256 "$ST")"
chk "B1 verdict_bytes == on-disk" "$RSZ" "$(jq -r .verdict_bytes "$ST")"
chk "B1 verdict_sha256 == file"  "$(sha "$RAW")"  "$(jq -r .verdict_sha256 "$ST")"
chk "B1 diag_bytes == on-disk"   "$DSZ" "$(jq -r .diagnostic_bytes "$ST")"
chk "B1 diag_sha256 == file"     "$(sha "$DIAG")" "$(jq -r .diagnostic_sha256 "$ST")"
chk "B1 diagnostic_output path"  "$DIAG" "$(jq -r .diagnostic_output "$ST")"
chk "B1 denied_count > 0" "ok" "$([ "$(jq -r .denied_count "$ST")" -gt 0 ] && echo ok || echo no)"
chk "B1 preserved_count=3" "3" "$(jq -r .preserved_count "$ST")"

# ── S1B-2: terminal-capable unknown → classification_untrusted even w/ later end ──
echo "── S1B-2: terminal-capable unknown → resource_rejected/classification_untrusted ──"
cat > "$TD/prodB.py" <<'PY'
import sys
w = sys.stdout.write
w('{"type":"weird_envelope","payload":{"deep":[{"required_actions":[]}]}}\n')  # unknown + terminal-capable
w('{"type":"text_delta","text":"still valid later"}\n')                        # valid end events follow
w('{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"end"}]}}\n')
w('{"type":"turn_end","message":{"stopReason":"stop"}}\n')
sys.stdout.flush()
PY
RAW="$TD/raw-b2.json"; ST="$TD/state-b2.json"; PIDS="$TD/pids-b2.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) \
  --task-id sup-b2 --task-id-source test \
  -- "$PY" "$TD/prodB.py" >/dev/null 2>&1
RC=$?
set -e
chk "B2 status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B2 supervisor exit=2" "2" "$RC"
chk "B2 reason has classification_untrusted" "y" "$(jq -r .reason "$ST" | grep -q classification_untrusted && echo y || echo n)"
chk "B2 terminal_capable_unknown_count>=1" "ok" "$([ "$(jq -r .terminal_capable_unknown_count "$ST")" -ge 1 ] && echo ok || echo no)"

# ── S1B-3: harmless unknown + valid end → reported, unknown counted, raw preserved-only ──
echo "── S1B-3: harmless unknown + valid end → reported ──"
cat > "$TD/prodC.py" <<'PY'
import sys
w = sys.stdout.write
w('{"type":"weird","foo":1,"bar":[1,2,{"baz":"qux"}]}\n')     # unknown, NOT terminal-capable
w('{"type":"text_delta","text":"hello world"}\n')
w('{"type":"turn_end","message":{"stopReason":"stop"}}\n')
sys.stdout.flush()
PY
RAW="$TD/raw-b3.json"; ST="$TD/state-b3.json"; PIDS="$TD/pids-b3.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) \
  --task-id sup-b3 --task-id-source test \
  -- "$PY" "$TD/prodC.py" >/dev/null 2>&1
RC=$?
set -e
chk "B3 status=reported" "reported" "$(jq -r .status "$ST")"
chk "B3 supervisor exit=0" "0" "$RC"
chk "B3 unknown_count=1" "1" "$(jq -r .unknown_count "$ST")"
chk "B3 terminal_capable_unknown_count=0" "0" "$(jq -r .terminal_capable_unknown_count "$ST")"
chk "B3 raw lines == preserved (2)" "2" "$(wc -l <"$RAW" | tr -d ' ')"
chk "B3 raw has no 'weird'" "0" "$(grep -c '"weird"' "$RAW" 2>/dev/null; true)"

# ── S1B-4: verdict cap breach AND ingress cap breach both fail closed, child reaped ──
echo "── S1B-4: verdict cap breach + ingress cap breach → resource_rejected, reaped ──"
cat > "$TD/prodVcap.py" <<'PY'
import sys
w = sys.stdout.write
for _ in range(1000):
    w('{"type":"text_delta","text":"' + "a"*500 + '"}\n')   # all preserve → verdict grows fast
sys.stdout.flush()
PY
RAW="$TD/raw-b4v.json"; ST="$TD/state-b4v.json"; PIDS="$TD/pids-b4v.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) --verdict-cap $((100*KIB)) \
  --task-id sup-b4v --task-id-source test \
  -- "$PY" "$TD/prodVcap.py" >/dev/null 2>&1
RC=$?
set -e
chk "B4v status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B4v supervisor exit=2" "2" "$RC"
chk "B4v reason has verdict_cap" "y" "$(jq -r .reason "$ST" | grep -q verdict_cap && echo y || echo n)"
chk "B4v raw <= verdict cap (exact)" "ok" "$([ "$(sz "$RAW")" -le $((100*KIB)) ] && echo ok || echo BREACH)"
chk "B4v raw_bytes == on-disk" "$(sz "$RAW")" "$(jq -r .raw_bytes "$ST")"
B4V_PID=$(jq -r .child_identity.pid "$ST")
if kill -0 "$B4V_PID" 2>/dev/null; then chk "B4v child reaped" gone alive; else chk "B4v child reaped" gone gone; fi

cat > "$TD/prodIcap.py" <<'PY'
import sys
w = sys.stdout.write
for _ in range(5000):
    w('{"type":"heartbeat","p":"' + "z"*900 + '"}\n')   # deny; ingress grows past cap
sys.stdout.flush()
PY
RAW="$TD/raw-b4i.json"; ST="$TD/state-b4i.json"; PIDS="$TD/pids-b4i.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((1*MIB)) \
  --task-id sup-b4i --task-id-source test \
  -- "$PY" "$TD/prodIcap.py" >/dev/null 2>&1
RC=$?
set -e
chk "B4i status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B4i supervisor exit=2" "2" "$RC"
chk "B4i reason has ingress_cap" "y" "$(jq -r .reason "$ST" | grep -q ingress_cap && echo y || echo n)"
chk "B4i raw digest matches file" "$(sha "$RAW")" "$(jq -r .raw_sha256 "$ST")"
B4I_PID=$(jq -r .child_identity.pid "$ST")
if kill -0 "$B4I_PID" 2>/dev/null; then chk "B4i child reaped" gone alive; else chk "B4i child reaped" gone gone; fi

# ── S1B-5: malformed/oversize line + classifier exception injection each fail closed ──
echo "── S1B-5: overlong line + classifier exception each fail closed ──"
cat > "$TD/prodBig.py" <<'PY'
import sys
sys.stdout.write('{"type":"text_delta","text":"' + "a"*(2*1024*1024) + '"}\n')  # > 1 MiB record
sys.stdout.flush()
PY
RAW="$TD/raw-b5o.json"; ST="$TD/state-b5o.json"; PIDS="$TD/pids-b5o.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) \
  --task-id sup-b5o --task-id-source test \
  -- "$PY" "$TD/prodBig.py" >/dev/null 2>&1
RC=$?
set -e
chk "B5 overlong status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B5 overlong exit=2" "2" "$RC"
chk "B5 overlong reason has overlong" "y" "$(jq -r .reason "$ST" | grep -q overlong && echo y || echo n)"

cat > "$TD/badcls.py" <<'PY'
def classify_jsonl_line(line_bytes, sequence):
    raise RuntimeError("injected classifier failure")
PY
cat > "$TD/prodOne.py" <<'PY'
import sys
sys.stdout.write('{"type":"text_delta","text":"x"}\n'); sys.stdout.flush()
PY
RAW="$TD/raw-b5c.json"; ST="$TD/state-b5c.json"; PIDS="$TD/pids-b5c.json"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) \
  --classifier-module "$TD/badcls.py" \
  --task-id sup-b5c --task-id-source test \
  -- "$PY" "$TD/prodOne.py" >/dev/null 2>&1
RC=$?
set -e
chk "B5 classifier-exc status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B5 classifier-exc exit=2" "2" "$RC"
chk "B5 classifier-exc reason" "y" "$(jq -r .reason "$ST" | grep -q classifier_exception && echo y || echo n)"

# ── S1B-6: diagnostic cap truncates while stream continues to reported final output ──
echo "── S1B-6: diagnostic cap truncated, still reported; digests match files ──"
cat > "$TD/prodDiag.py" <<'PY'
import sys
w = sys.stdout.write
for _ in range(4000):
    w('{"type":"heartbeat","p":"' + "q"*100 + '"}\n')     # many deny → diag grows past small cap
w('{"type":"text_delta","text":"final visible"}\n')
w('{"type":"turn_end","message":{"stopReason":"stop"}}\n')
sys.stdout.flush()
PY
RAW="$TD/raw-b6.json"; ST="$TD/state-b6.json"; PIDS="$TD/pids-b6.json"; DIAG="$RAW.diag.jsonl"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) --diagnostic-cap $((64*KIB)) \
  --task-id sup-b6 --task-id-source test \
  -- "$PY" "$TD/prodDiag.py" >/dev/null 2>&1
RC=$?
set -e
chk "B6 status=reported" "reported" "$(jq -r .status "$ST")"
chk "B6 supervisor exit=0" "0" "$RC"
chk "B6 diagnostic_truncated=true" "true" "$(jq -r .diagnostic_truncated "$ST")"
chk "B6 diag <= diag cap" "ok" "$([ "$(sz "$DIAG")" -le $((64*KIB)) ] && echo ok || echo too_big)"
chk "B6 diag_bytes == on-disk" "$(sz "$DIAG")" "$(jq -r .diagnostic_bytes "$ST")"
chk "B6 diag_sha256 == file" "$(sha "$DIAG")" "$(jq -r .diagnostic_sha256 "$ST")"
chk "B6 raw_sha256 == file" "$(sha "$RAW")" "$(jq -r .raw_sha256 "$ST")"
chk "B6 raw has final visible" "y" "$(grep -q 'final visible' "$RAW" && echo y || echo n)"

# ── S1B-7: setsid descendant writes stdout after parent exit; ingress cap contains it ──
echo "── S1B-7: capture-mode setsid escapee bounded by ingress cap; direct child reaped ──"
B7SIDE="$TD/b7-grandchild.txt"
cat > "$TD/escapeeB.py" <<'PY'
import os, sys
SIDE = sys.argv[1]
pid = os.fork()
if pid > 0:
    os._exit(0)                       # direct child exits immediately
os.setsid()                            # grandchild escapes into its own session
with open(SIDE, "w") as fh:
    fh.write(str(os.getpid()))
line = b'{"type":"heartbeat","p":"' + b"h"*3000 + b'"}\n'   # newline-framed deny lines
try:
    for _ in range(8000):              # attempt ~24 MiB; ingress cap must trip far earlier
        os.write(1, line)
except OSError:
    pass                               # EPIPE once supervisor closes the read end
with open(SIDE, "a") as fh:
    fh.write(":done")
os._exit(0)
PY
RAW="$TD/raw-b7.json"; ST="$TD/state-b7.json"; PIDS="$TD/pids-b7.json"; DIAG="$RAW.diag.jsonl"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((512*KIB)) \
  --verdict-cap $((1*MIB)) --diagnostic-cap $((512*KIB)) \
  --task-id sup-b7 --task-id-source test \
  -- "$PY" "$TD/escapeeB.py" "$B7SIDE" >/dev/null 2>&1
RC=$?
set -e
GPID=$( { sed 's/:done//' "$B7SIDE" 2>/dev/null || true; } | tr -d ' ')
for _ in $(seq 1 100); do grep -q ":done" "$B7SIDE" 2>/dev/null && break; sleep 0.05; done
chk "B7 status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B7 supervisor exit=2" "2" "$RC"
chk "B7 reason has ingress_cap" "y" "$(jq -r .reason "$ST" | grep -q ingress_cap && echo y || echo n)"
B7_PID=$(jq -r .child_identity.pid "$ST")
if kill -0 "$B7_PID" 2>/dev/null; then chk "B7 direct child reaped" gone alive; else chk "B7 direct child reaped" gone gone; fi
chk "B7 raw <= verdict cap" "ok" "$([ "$(sz "$RAW")" -le $((1*MIB)) ] && echo ok || echo too_big)"
chk "B7 diag <= diag cap" "ok" "$([ "$(sz "$DIAG")" -le $((512*KIB)) ] && echo ok || echo too_big)"
chk "B7 raw_bytes == on-disk" "$(sz "$RAW")" "$(jq -r .raw_bytes "$ST")"
chk "B7 raw digest matches file" "$(sha "$RAW")" "$(jq -r .raw_sha256 "$ST")"
[[ -n "$GPID" ]] && kill -9 "$GPID" 2>/dev/null || true   # safety net

# ── S1B-8: capture state fields/digests exact; legacy has NONE of the new fields ──
echo "── S1B-8: capture fields exact; legacy invocation has no capture fields ──"
cat > "$TD/prodTiny.py" <<'PY'
import sys
w = sys.stdout.write
w('{"type":"text_delta","text":"one"}\n')
w('{"type":"turn_end","message":{"stopReason":"stop"}}\n')
sys.stdout.flush()
PY
RAW="$TD/raw-b8.json"; ST="$TD/state-b8.json"; PIDS="$TD/pids-b8.json"; DIAG="$RAW.diag.jsonl"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) \
  --task-id sup-b8 --task-id-source test \
  -- "$PY" "$TD/prodTiny.py" >/dev/null 2>&1
set -e
# All additive capture fields present and exact.
CAPFIELDS="capture_mode diagnostic_output ingress_bytes ingress_lines ingress_sha256 \
verdict_bytes verdict_lines verdict_sha256 diagnostic_bytes diagnostic_lines \
diagnostic_sha256 diagnostic_truncated preserved_count denied_count \
unknown_count terminal_capable_unknown_count"
B8_MISSING=""
for k in $CAPFIELDS; do
  jq -e "has(\"$k\")" "$ST" >/dev/null 2>&1 || B8_MISSING="$B8_MISSING $k"
done
chk "B8 all 16 capture fields present" "" "$B8_MISSING"
chk "B8 verdict digest exact" "$(sha "$RAW")" "$(jq -r .verdict_sha256 "$ST")"
chk "B8 verdict_bytes exact" "$(sz "$RAW")" "$(jq -r .verdict_bytes "$ST")"
chk "B8 ingress_lines exact" "2" "$(jq -r .ingress_lines "$ST")"
chk "B8 preserved_count=2" "2" "$(jq -r .preserved_count "$ST")"
chk "B8 raw==verdict (canonical raw is verdict raw)" "$(jq -r .verdict_sha256 "$ST")" "$(jq -r .raw_sha256 "$ST")"

# Legacy invocation: NONE of the capture fields may exist.
RAWL="$TD/raw-b8l.json"; STL="$TD/state-b8l.json"; PIDSL="$TD/pids-b8l.json"
set +e
"$PY" "$SUP" --state-file "$STL" --raw-output "$RAWL" \
  --raw-cap $((20*MIB)) --pid-store "$PIDSL" \
  --task-id sup-b8l --task-id-source test \
  -- "$PY" "$TD/prodTiny.py" >/dev/null 2>&1
set -e
LEGACY_HAS=$(for k in capture_mode diagnostic_output ingress_bytes verdict_bytes diagnostic_bytes preserved_count; do jq -e "has(\"$k\")" "$STL" >/dev/null 2>&1 && echo yes || true; done)
chk "B8 legacy status=reported" "reported" "$(jq -r .status "$STL")"
chk "B8 legacy has NO capture fields" "" "$LEGACY_HAS"

# ── S1B-9 (return1/B1): rate fuse restored in verdict_v1, on physical ingress ──
echo "── S1B-9: verdict_v1 rate fuse trips on sustained ingress, child reaped ──"
cat > "$TD/prodRate.py" <<'PY'
import sys, time
line = '{"type":"heartbeat","p":"' + "z"*1000 + '"}\n'   # deny, ~1 KiB each
# ~6 MiB/s: ~600 KiB per 0.1s burst; window 0.5s sees ~3 MiB >> 1 MiB threshold.
for _ in range(60):
    for _ in range(600):
        sys.stdout.write(line)
    sys.stdout.flush()
    time.sleep(0.1)
PY
RAW="$TD/raw-b9.json"; ST="$TD/state-b9.json"; PIDS="$TD/pids-b9.json"; DIAG="$RAW.diag.jsonl"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((50*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((50*MIB)) \
  --rate-window-bytes $((1*MIB)) --rate-window-seconds 0.5 --rate-fuse-windows 2 \
  --task-id sup-b9 --task-id-source test \
  -- "$PY" "$TD/prodRate.py" >/dev/null 2>&1
RC=$?
set -e
chk "B9 status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B9 supervisor exit=2" "2" "$RC"
chk "B9 reason has rate_fuse" "y" "$(jq -r .reason "$ST" | grep -q rate_fuse && echo y || echo n)"
chk "B9 rate_fuse.enabled=true" "true" "$(jq -r .rate_fuse.enabled "$ST")"
chk "B9 rate_fuse.window_bytes" "$((1*MIB))" "$(jq -r .rate_fuse.window_bytes "$ST")"
chk "B9 rate_fuse.window_seconds" "0.5" "$(jq -r .rate_fuse.window_seconds "$ST")"
chk "B9 rate_fuse.fuse_windows" "2" "$(jq -r .rate_fuse.fuse_windows "$ST")"
chk "B9 consecutive_over >= fuse_windows" "ok" "$([ "$(jq -r .rate_fuse.consecutive_over "$ST")" -ge 2 ] && echo ok || echo no)"
chk "B9 capture_mode=verdict_v1" "verdict_v1" "$(jq -r .capture_mode "$ST")"
B9_PID=$(jq -r .child_identity.pid "$ST")
if kill -0 "$B9_PID" 2>/dev/null; then chk "B9 direct child reaped" gone alive; else chk "B9 direct child reaped" gone gone; fi
chk "B9 raw <= verdict cap" "ok" "$([ "$(sz "$RAW")" -le $((1*MIB)) ] && echo ok || echo too_big)"
chk "B9 diag <= diag cap" "ok" "$([ "$(sz "$DIAG")" -le $((512*KIB)) ] && echo ok || echo too_big)"
chk "B9 raw digest matches file" "$(sha "$RAW")" "$(jq -r .raw_sha256 "$ST")"

# ── S1B-10 (return1/B2): select/read fault fails closed, never synthetic success ──
# In-process harness: import supervisor, monkeypatch its select.select to raise
# OSError while the child sleeps. Must return 2 / resource_rejected /
# capture_io_error and the direct child must be dead. Harness TERM/KILLs by
# recorded PGID in finally so no residual process even if the test fails.
echo "── S1B-10: select fault → capture_io_error, fail closed, child gone ──"
S1B_10=$("$PY" - "$SUP" "$TD" <<'PY'
import importlib.util, sys, os, json, signal, time
SUP = sys.argv[1]; TD = sys.argv[2]
spec = importlib.util.spec_from_file_location("supv_fault", SUP)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
st = f"{TD}/st-b10.json"; raw = f"{TD}/raw-b10.json"; pids = f"{TD}/pids-b10.json"
orig_select = m.select.select
def boom(*a, **k):
    raise OSError(9, "Bad file descriptor")
rc = None
pgid = None
try:
    m.select.select = boom
    sys.argv = ["supv_fault", "--state-file", st, "--raw-output", raw,
                "--raw-cap", str(20 * 1024 * 1024), "--pid-store", pids,
                "--capture-mode", "verdict_v1", "--ingress-cap", str(30 * 1024 * 1024),
                "--task-id", "b10", "--task-id-source", "test",
                "--", "sleep", "5"]
    rc = m.main()
    d = json.load(open(st))
    try:
        pgid = json.load(open(pids)).get("pgid")
    except Exception:
        pgid = d.get("child_identity", {}).get("pgid")
    pid = d["child_identity"]["pid"]
    alive = True
    try:
        os.kill(pid, 0)
    except OSError:
        alive = False
    ok = (
        rc == 2
        and d["status"] == "resource_rejected"
        and "capture_io_error" in d["reason"]
        and alive is False
    )
    print("ok" if ok else "bad")
finally:
    m.select.select = orig_select
    # 兜底：无论测试成败，用记录的 PGID TERM/KILL，杜绝残留进程。
    if pgid:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(pgid, sig)
            except OSError:
                pass
            time.sleep(0.05)
PY
)
chk "B10 select fault fails closed (capture_io_error, child gone)" "ok" "$S1B_10"

# ── S1B-11 (EOF-framing): valid framed records then an EOF no-newline
#    terminal-shaped JSON tail → resource_rejected/incomplete_final_record.
# L2 found an EOF-terminal-unknown bypass: a syntactically valid, terminal-shaped
# object (e.g. turn_end) that arrives WITHOUT a trailing newline used to be handed
# to the classifier at EOF. verdict_v1 is newline-delimited JSONL — an unterminated
# final record is framing-invalid and must fail closed WITHOUT classifying it. The
# tail body (TAILCANARY) must never reach raw/diag/state, no verdict is preserved
# for it, and the direct child must be reaped.
echo "── S1B-11: EOF no-newline terminal-shaped tail → incomplete_final_record ──"
TAILCANARY="TAILCANARY_EOF_9z1x"
cat > "$TD/prodEOF.py" <<PY
import sys
w = sys.stdout.write
# Valid, newline-framed assistant text (complete records) — these DO land in raw.
w('{"type":"text_delta","text":"visible framed answer"}\n')
w('{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"clean end"}]}}\n')
# EOF no-newline terminal-shaped JSON object: syntactically valid turn_end, but NO
# trailing newline → framing-invalid tail carrying a distinctive marker.
w('{"type":"turn_end","message":{"stopReason":"stop"},"tail":"$TAILCANARY"}')
sys.stdout.flush()
PY
RAW="$TD/raw-b11.json"; ST="$TD/state-b11.json"; PIDS="$TD/pids-b11.json"; DIAG="$RAW.diag.jsonl"
set +e
"$PY" "$SUP" --state-file "$ST" --raw-output "$RAW" \
  --raw-cap $((20*MIB)) --pid-store "$PIDS" \
  --capture-mode verdict_v1 --ingress-cap $((30*MIB)) \
  --task-id sup-b11 --task-id-source test \
  -- "$PY" "$TD/prodEOF.py" >/dev/null 2>&1
RC=$?
set -e
chk "B11 status=resource_rejected" "resource_rejected" "$(jq -r .status "$ST")"
chk "B11 supervisor exit=2" "2" "$RC"
chk "B11 reason has incomplete_final_record" "y" "$(jq -r .reason "$ST" | grep -q incomplete_final_record && echo y || echo n)"
# The tail body must NOT appear anywhere: raw, diag, or state.
chk "B11 no tail body in raw"   "0" "$(grep -c "$TAILCANARY" "$RAW"  2>/dev/null; true)"
chk "B11 no tail body in diag"  "0" "$(grep -c "$TAILCANARY" "$DIAG" 2>/dev/null; true)"
chk "B11 no tail body in state" "0" "$(grep -c "$TAILCANARY" "$ST"   2>/dev/null; true)"
# No verdict preserved for the tail turn_end; the tail's terminal shape must not
# be counted as preserved. Only the two earlier valid records are preserved.
chk "B11 preserved_count=2 (tail not preserved)" "2" "$(jq -r .preserved_count "$ST")"
chk "B11 raw has no turn_end (tail unframed)" "0" "$(grep -c '"type":"turn_end"' "$RAW" 2>/dev/null; true)"
# Earlier valid framed records are unaffected and DO land in raw.
chk "B11 raw has earlier text_delta" "y" "$(grep -q '"type":"text_delta"' "$RAW" && echo y || echo n)"
# Direct child must be reaped, and state digests must describe the real files.
B11_PID=$(jq -r .child_identity.pid "$ST")
if kill -0 "$B11_PID" 2>/dev/null; then chk "B11 direct child reaped" gone alive; else chk "B11 direct child reaped" gone gone; fi
chk "B11 raw digest matches file" "$(sha "$RAW")" "$(jq -r .raw_sha256 "$ST")"
chk "B11 raw_bytes == on-disk" "$(sz "$RAW")" "$(jq -r .raw_bytes "$ST")"

echo
echo "════════ PASS=$P FAIL=$F ════════"
[[ $F -eq 0 ]] && exit 0 || exit 1
