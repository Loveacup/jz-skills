#!/usr/bin/env bash
# test-gc.sh — TDD test for cc-gc.sh (P0-3, PRD R9c 堆积检测 + R9d Session GC)
#
# HERMETIC: no real tmux, no real /tmp pollution. Inject a stub tmux via CC_GC_TMUX
# and point all state files at a throwaway dir via CC_GC_TMPDIR.
#   stub reads:  $D/sessions.txt (list-sessions) · $D/alive/<s> (has-session) · $D/pane/<s>.txt (capture-pane)
#   cc-gc reads: $D/cc-lock-<t>/session · $D/cc-heartbeat-<s> · $D/cc-turn-done-<s> · $D/cc-output/<s>/
# Machine assertion lines on stderr: GCMETA … / GCITEM … / GCAPPLY …
#
# Covers: 僵尸 · 完成 · IDLE>2h · 总数超限(overflow) · 活跃跳过 · 安全规则(只读默认/--apply/产物提醒)

set -euo pipefail

GC="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-gc.sh"
PASS=0 FAIL=0
D=""   # per-test sandbox

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# ── build a fresh hermetic sandbox + stub tmux ──
new_sandbox() {
  D=$(mktemp -d "/tmp/cc-gc-test.XXXXXX")
  mkdir -p "$D/alive" "$D/pane" "$D/cc-output"
  : > "$D/sessions.txt"
  cat > "$D/stub-tmux.sh" <<'STUB'
#!/usr/bin/env bash
D="$CC_GC_STUB_DIR"
cmd="${1:-}"; shift || true
name=""
while [[ $# -gt 0 ]]; do [[ "$1" == "-t" ]] && { name="${2:-}"; shift 2; continue; }; shift; done
case "$cmd" in
  list-sessions) cat "$D/sessions.txt" 2>/dev/null ;;
  has-session)   [[ -f "$D/alive/$name" ]] && exit 0 || exit 1 ;;
  capture-pane)  cat "$D/pane/$name.txt" 2>/dev/null ;;
  *) exit 0 ;;
esac
STUB
  chmod +x "$D/stub-tmux.sh"
}
cleanup() { [[ -n "$D" && -d "$D" ]] && rm -rf "$D"; }
trap cleanup EXIT

# add an ALIVE session with a given pane fixture
add_session() { # <name> <pane-content>
  echo "$1" >> "$D/sessions.txt"
  : > "$D/alive/$1"
  printf '%s\n' "$2" > "$D/pane/$1.txt"
}
# run cc-gc with sandbox wired in; capture stderr (machine lines)
run_gc() { CC_GC_TMUX="bash $D/stub-tmux.sh" CC_GC_STUB_DIR="$D" CC_GC_TMPDIR="$D" \
            bash "$GC" "$@" 2>&1 >/dev/null; }

PANE_IDLE='⏺ done earlier
❯ '
PANE_THINK='✻ Thinking about it…'
PANE_TOOL='⏺ Writing file…'

echo "=== cc-gc TDD: Session 垃圾回收 (P0-3) ==="
echo ""

# ── TC1: zombie — lock dir points to a DEAD session ──
new_sandbox
mkdir -p "$D/cc-lock-jz-skills"; echo "hermes-cc-default-jz-skills-0101-0000" > "$D/cc-lock-jz-skills/session"
err=$(run_gc --mode gc || true)
if grep -q 'GCITEM kind=zombie .*session=hermes-cc-default-jz-skills-0101-0000' <<<"$err"; then
  ok "TC1 僵尸识别 (锁存在 + session 已死)"
else no "TC1 僵尸未识别 ($(grep GCITEM <<<"$err" | head -c 100))"; fi
cleanup

# ── TC2: zombie --apply → lock dir + state files removed ──
new_sandbox
mkdir -p "$D/cc-lock-foo"; echo "hermes-cc-x-foo-0101-0000" > "$D/cc-lock-foo/session"
: > "$D/cc-state-hermes-cc-x-foo-0101-0000.log"
run_gc --mode gc --apply >/dev/null 2>&1 || true
if [[ ! -d "$D/cc-lock-foo" ]] && [[ ! -f "$D/cc-state-hermes-cc-x-foo-0101-0000.log" ]]; then
  ok "TC2 僵尸 --apply 清理锁目录 + state 文件"
else no "TC2 --apply 未清理 (lock_exists=$([[ -d "$D/cc-lock-foo" ]] && echo y||echo n))"; fi
cleanup

# ── TC3: safety rule 1 — gc WITHOUT --apply mutates nothing ──
new_sandbox
mkdir -p "$D/cc-lock-foo"; echo "hermes-cc-x-foo-0101-0000" > "$D/cc-lock-foo/session"
run_gc --mode gc >/dev/null 2>&1 || true
if [[ -d "$D/cc-lock-foo" ]]; then
  ok "TC3 安全规则1：gc 默认只读，不删僵尸锁（无 --apply）"
else no "TC3 gc 默认竟删了僵尸锁（违反干运行）"; fi
cleanup

# ── TC4: completed — turn-done + alive + IDLE → kind=completed ──
new_sandbox
S="hermes-cc-default-jz-skills-0202-0000"; add_session "$S" "$PANE_IDLE"
: > "$D/cc-turn-done-$S"
err=$(run_gc --mode gc || true)
if grep -q "GCITEM kind=completed .*session=$S" <<<"$err"; then
  ok "TC4 完成识别 (turn-done + 存活 + IDLE)"
else no "TC4 完成未识别 ($(grep GCITEM <<<"$err" | head -c 120))"; fi
cleanup

# ── TC5: IDLE>2h — aged heartbeat, no turn-done → kind=idle2h ──
new_sandbox
S="hermes-cc-default-jz-skills-0303-0000"; add_session "$S" "$PANE_IDLE"
echo "0|1|IDLE|?|0|1|?" > "$D/cc-heartbeat-$S"
touch -t "$(date -v-3H +%Y%m%d%H%M)" "$D/cc-heartbeat-$S"
err=$(run_gc --mode gc || true)
if grep -q "GCITEM kind=idle2h .*session=$S" <<<"$err"; then
  ok "TC5 IDLE>2h 识别 (心跳陈旧 + 非 turn-done)"
else no "TC5 IDLE>2h 未识别 ($(grep GCITEM <<<"$err" | head -c 120))"; fi
cleanup

# ── TC6: active skip (safety rule 2) — THINKING never a candidate ──
new_sandbox
S="hermes-cc-default-jz-skills-0404-0000"; add_session "$S" "$PANE_THINK"
: > "$D/cc-turn-done-$S"   # even with a stale turn-done, an active pane must NOT be a candidate
err=$(run_gc --mode gc || true)
if grep -q "GCITEM kind=active-skip .*session=$S" <<<"$err" \
   && ! grep -qE "GCITEM kind=(completed|idle2h|zombie) .*session=$S" <<<"$err"; then
  ok "TC6 安全规则2：活跃(THINKING)跳过，不入候选"
else no "TC6 活跃未跳过 ($(grep GCITEM <<<"$err" | head -c 160))"; fi
cleanup

# ── TC7: heap detection R9c — >3 residual hermes-cc → heap_warn=1 ──
new_sandbox
for i in 1 2 3 4; do add_session "hermes-cc-a-t$i-0505-000$i" "$PANE_IDLE"; done
err=$(run_gc --mode scan || true)
if grep -qE 'GCMETA .*heap_warn=1' <<<"$err"; then
  ok "TC7 堆积检测 R9c：>3 残留 → heap_warn=1"
else no "TC7 堆积未告警 ($(grep GCMETA <<<"$err" | head -c 120))"; fi
cleanup

# ── TC8: overflow R9d cond4 — >8 active → overflow=1 + lists oldest ──
new_sandbox
for i in $(seq 1 9); do add_session "hermes-cc-a-o$i-0606-000$i" "$PANE_THINK"; done
err=$(run_gc --mode scan || true)
if grep -qE 'GCMETA .*overflow=1' <<<"$err" && grep -q 'GColdest ' <<<"$err"; then
  ok "TC8 总数超限 R9d cond4：>8 活跃 → overflow=1 + 列出最旧"
else no "TC8 overflow 未触发 ($(grep -E 'GCMETA|GColdest' <<<"$err" | head -c 140))"; fi
cleanup

# ── TC9: safety rule 3 — completed with artifacts → artifacts count surfaced ──
new_sandbox
S="hermes-cc-default-jz-skills-0707-0000"; add_session "$S" "$PANE_IDLE"
: > "$D/cc-turn-done-$S"; mkdir -p "$D/cc-output/$S"; : > "$D/cc-output/$S/result.md"; : > "$D/cc-output/$S/notes.txt"
err=$(run_gc --mode gc || true)
if grep -qE "GCITEM kind=completed .*session=$S .*artifacts=2" <<<"$err"; then
  ok "TC9 安全规则3：completed 候选附产物计数 (artifacts=2)"
else no "TC9 产物计数缺失 ($(grep GCITEM <<<"$err" | head -c 160))"; fi
cleanup

# ── TC10: suggest mode — one-line summary on stdout ──
new_sandbox
S="hermes-cc-default-jz-skills-0808-0000"; add_session "$S" "$PANE_IDLE"; : > "$D/cc-turn-done-$S"
out=$(CC_GC_TMUX="bash $D/stub-tmux.sh" CC_GC_STUB_DIR="$D" CC_GC_TMPDIR="$D" bash "$GC" --mode suggest 2>/dev/null || true)
if grep -qE '可 kill|可清理|建议' <<<"$out" && [[ "$(wc -l <<<"$out" | tr -d ' ')" -le 3 ]]; then
  ok "TC10 suggest 模式：简洁建议 (≤3 行)"
else no "TC10 suggest 输出异常 ($(head -c 120 <<<"$out"))"; fi
cleanup

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
