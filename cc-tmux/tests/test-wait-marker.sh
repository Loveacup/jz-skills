#!/usr/bin/env bash
# test-wait-marker.sh — TDD for cc-wait-marker.sh (§3 In-Turn Wait)
#
# cc-wait-marker.sh blocks until a turn-done marker NEWER than --after appears,
# so Hermes can `process(action=wait)` on it inside a single turn and loop
# send → wait → read → send. Contract under test:
#   --session <name>   build marker path /private/tmp/cc-turn-done-<name>
#   --after <epoch>    block until mtime(marker) > after  (strict >)
#   --timeout <secs>   default 21600; on expiry exit 1
#   exit 0 + cat marker → a marker strictly newer than --after appeared
#   exit 1             → timeout, no newer marker
#   exit 2 + stderr    → bad/missing args (e.g. no --session)
#   poll interval 2s, paths under /private/tmp (macOS symlink)
#
# NOTE on Test 3: the task spec's literal "--after N+100" contradicts the
# core contract ("block until mtime > after") and Test 6. The spec's own
# parenthetical "(marker 存在且更新)" reveals the intent: a marker ALREADY
# NEWER than --after → immediate exit 0. We therefore encode Test 3 as
# marker mtime=N with --after = N-100 (after is OLDER than the marker).
# Flagged for confirmation at the RED review gate.

set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-wait-marker.sh"
SESS="cctmux-test-waitmarker-$$"
MARKER="/private/tmp/cc-turn-done-${SESS}"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
cleanup(){ rm -f "$MARKER" "/tmp/cc-turn-done-${SESS}"; }
trap cleanup EXIT
cleanup

# Wait up to $1 seconds for pid $2 to exit; returns when dead or on deadline.
wait_pid_exit(){
  local secs="$1" pid="$2" i=0
  while [[ "$i" -lt "$secs" ]]; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 1; i=$((i+1))
  done
  return 1
}

echo "=== cc-wait-marker TDD: in-turn wait on turn-done marker (§3) ==="
echo ""

# ── Test 1: a NEWER marker appears after start → exit 0, stdout = marker content ──
printf 'OLD\n' > "$MARKER"
touch -t 202601010000.00 "$MARKER" 2>/dev/null || true   # old mtime (2026-01-01)
AFTER=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
outf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after "$AFTER" --timeout 30 >"$outf" 2>/dev/null &
pid=$!
sleep 1
printf 'DONE-1\n' > "$MARKER"        # fresh mtime (now) > AFTER
if wait_pid_exit 10 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 0 ]] && grep -q 'DONE-1' "$outf"; then
    ok "newer marker after start → exit 0 + emits marker content"
  else
    bad "newer marker: rc=$rc out='$(tr -d '\n' <"$outf")'"
  fi
else
  kill "$pid" 2>/dev/null; bad "newer marker: script never exited"
fi
rm -f "$outf"

# ── Test 2: no marker at start, --after 0, marker appears → exit 0 + content ──
rm -f "$MARKER"
outf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >"$outf" 2>/dev/null &
pid=$!
sleep 1
printf 'DONE-2\n' > "$MARKER"
if wait_pid_exit 10 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 0 ]] && grep -q 'DONE-2' "$outf"; then
    ok "no prior marker, --after 0 → waits then exit 0 + content"
  else
    bad "no-prior-marker: rc=$rc out='$(tr -d '\n' <"$outf")'"
  fi
else
  kill "$pid" 2>/dev/null; bad "no-prior-marker: script never exited"
fi
rm -f "$outf"

# ── Test 3: marker already NEWER than --after → immediate exit 0 + content ──
# (See header NOTE: spec's "--after N+100" reinterpreted as marker newer than after.)
printf 'DONE-3\n' > "$MARKER"
N=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
AFTER=$((N - 100))
outf=$(mktemp)
start=$(date +%s)
bash "$SCRIPT" --session "$SESS" --after "$AFTER" --timeout 30 >"$outf" 2>/dev/null
rc=$?
elapsed=$(( $(date +%s) - start ))
if [[ "$rc" -eq 0 ]] && grep -q 'DONE-3' "$outf" && [[ "$elapsed" -lt 3 ]]; then
  ok "marker already newer than --after → immediate exit 0 (${elapsed}s) + content"
else
  bad "already-newer: rc=$rc elapsed=${elapsed}s out='$(tr -d '\n' <"$outf")'"
fi
rm -f "$outf"

# ── Test 4: no marker, --timeout 3 → exit 1 after ~timeout ──
rm -f "$MARKER"
start=$(date +%s)
bash "$SCRIPT" --session "$SESS" --after 0 --timeout 3 >/dev/null 2>&1
rc=$?
elapsed=$(( $(date +%s) - start ))
if [[ "$rc" -eq 1 ]] && [[ "$elapsed" -ge 3 ]] && [[ "$elapsed" -lt 12 ]]; then
  ok "no marker, --timeout 3 → exit 1 (after ${elapsed}s)"
else
  bad "timeout: rc=$rc elapsed=${elapsed}s (want rc=1, 3<=t<12)"
fi

# ── Test 5: missing --session → exit 2 + stderr message ──
err=$(bash "$SCRIPT" --after 0 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "missing --session → exit 2 + stderr"
else
  bad "arg-validation: rc=$rc (want 2) stderr='$(printf '%s' "$err" | tr -d '\n')'"
fi

# ── Test 6: marker NOT newer than --after → blocks (does not exit) ──
printf 'STALE\n' > "$MARKER"
N=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
bash "$SCRIPT" --session "$SESS" --after "$N" --timeout 30 >/dev/null 2>&1 &
pid=$!
sleep 3
if kill -0 "$pid" 2>/dev/null; then
  ok "marker not newer than --after → still blocking after 3s"
  kill "$pid" 2>/dev/null
else
  bad "marker not newer → exited early (should block)"
fi
wait "$pid" 2>/dev/null || true

# ── Test 7: unknown arg → exit 2 + stderr ──
err=$(bash "$SCRIPT" --session "$SESS" --bogus 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "unknown arg → exit 2 + stderr"
else
  bad "unknown-arg: rc=$rc (want 2) stderr='$(printf '%s' "$err" | tr -d '\n')'"
fi

# ── Test 8: -h/--help → exit 0 + usage on stderr ──
out=$(bash "$SCRIPT" --help 2>&1); rc=$?
if [[ "$rc" -eq 0 ]] && printf '%s' "$out" | grep -qi 'usage'; then
  ok "--help → exit 0 + usage"
else
  bad "help: rc=$rc (want 0) out='$(printf '%s' "$out" | tr -d '\n' | cut -c1-40)'"
fi

# ── Test 9: --after as trailing arg with no value → exit 2 (not unbound crash) ──
err=$(bash "$SCRIPT" --session "$SESS" --after 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "--after missing value → exit 2 + stderr"
else
  bad "after-missing-value: rc=$rc (want 2; rc=1 = set -u unbound crash)"
fi

# ── Test 10: --timeout as trailing arg with no value → exit 2 (not unbound crash) ──
err=$(bash "$SCRIPT" --session "$SESS" --timeout 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "--timeout missing value → exit 2 + stderr"
else
  bad "timeout-missing-value: rc=$rc (want 2; rc=1 = set -u unbound crash)"
fi

# ── Test 11: non-numeric --after → exit 2 (input validation, no hang/late timeout) ──
errf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after notanum --timeout 5 >/dev/null 2>"$errf" &
pid=$!
if wait_pid_exit 6 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 2 ]] && [[ -s "$errf" ]]; then
    ok "non-numeric --after → exit 2 + stderr"
  else
    bad "non-numeric-after: rc=$rc (want 2; rc=1 = blocked to timeout, no validation)"
  fi
else
  kill "$pid" 2>/dev/null; bad "non-numeric-after: never exited (no validation, would hang)"
fi
rm -f "$errf"

# ── Test 12: non-numeric --timeout → exit 2 (must not infinite-loop on bad arith) ──
errf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after 0 --timeout notanum >/dev/null 2>"$errf" &
pid=$!
if wait_pid_exit 6 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 2 ]] && [[ -s "$errf" ]]; then
    ok "non-numeric --timeout → exit 2 + stderr"
  else
    bad "non-numeric-timeout: rc=$rc (want 2)"
  fi
else
  kill "$pid" 2>/dev/null; bad "non-numeric-timeout: never exited (infinite loop on bad arith)"
fi
rm -f "$errf"

# ═══ P1-2: fswatch 事件驱动等待（CC_WAIT_FSWATCH 注入 stub，hermetic）═══
echo ""
echo "§P1-2 fswatch 事件驱动等待（mock fswatch via CC_WAIT_FSWATCH）"

# stub 工厂：写一个假 fswatch 到临时文件，行为由 $1 决定（quick=立即返回 / hang=永挂）
STUBDIR=$(mktemp -d "/tmp/cc-wm-stub.XXXXXX")
trap 'rm -f "$MARKER" "/tmp/cc-turn-done-${SESS}"; rm -rf "$STUBDIR"' EXIT
make_fswatch() { # <name> <quick|hang> — stub touches <p>.called on invocation (proves fswatch path used)
  local p="$STUBDIR/$1"
  if [[ "$2" == "quick" ]]; then
    printf '#!/usr/bin/env bash\ntouch "%s.called"\nsleep 0.1\nexit 0\n' "$p" > "$p"   # 模拟「事件已触发」立即返回
  else
    printf '#!/usr/bin/env bash\ntouch "%s.called"\nsleep 999\n' "$p" > "$p"            # 模拟永挂（等不到事件）
  fi
  chmod +x "$p"; echo "$p"
}

# ── Test 13: fswatch 路径 — stub 立即返回，核心循环捕获新 marker → exit 0 + 内容 ──
rm -f "$MARKER"
printf 'OLD\n' > "$MARKER"; touch -t 202601010000.00 "$MARKER" 2>/dev/null || true
AFTER=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
FSW=$(make_fswatch fsw-quick quick)
outf=$(mktemp)
CC_WAIT_FSWATCH="$FSW" bash "$SCRIPT" --session "$SESS" --after "$AFTER" --timeout 30 >"$outf" 2>/dev/null &
pid=$!
sleep 1
printf 'DONE-13\n' > "$MARKER"        # fresh mtime > AFTER；stub 每 0.1s 返回 → 循环顶复判捕获
if wait_pid_exit 10 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  # 断言机制：stub 被调用过（旧轮询码不会调 → RED）+ 行为 exit 0 + 内容
  if [[ "$rc" -eq 0 ]] && grep -q 'DONE-13' "$outf" && [[ -f "${FSW}.called" ]]; then
    ok "fswatch 路径：真调 fswatch stub + 复判 → exit 0 + 内容"
  else
    bad "fswatch-path: rc=$rc called=$([[ -f "${FSW}.called" ]]&&echo y||echo n) out='$(tr -d '\n' <"$outf")'"
  fi
else
  kill "$pid" 2>/dev/null; bad "fswatch-path: never exited"
fi
rm -f "$outf"

# ── Test 14: 回退路径 — CC_WAIT_FSWATCH 指向不存在命令 → 回退轮询，marker 出现仍 exit 0 ──
rm -f "$MARKER"
outf=$(mktemp)
CC_WAIT_FSWATCH="/nonexistent/fswatch-xyz" bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >"$outf" 2>/dev/null &
pid=$!
sleep 1
printf 'DONE-14\n' > "$MARKER"
if wait_pid_exit 10 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 0 ]] && grep -q 'DONE-14' "$outf"; then
    ok "回退路径：fswatch 不可用 → 轮询兜底，marker 出现 → exit 0 + 内容"
  else
    bad "fallback-path: rc=$rc out='$(tr -d '\n' <"$outf")'"
  fi
else
  kill "$pid" 2>/dev/null; bad "fallback-path: never exited"
fi
rm -f "$outf"

# ── Test 15: 超时包裹 — stub 永挂 + 短 timeout → bash 超时 kill → exit 1（非 999） ──
rm -f "$MARKER"
printf 'STALE\n' > "$MARKER"
N=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)   # marker 存在但不会更新
FSW=$(make_fswatch fsw-hang hang)
start=$(date +%s)
CC_WAIT_SKIP_START_GATE=1 CC_WAIT_FSWATCH="$FSW" bash "$SCRIPT" --session "$SESS" --after "$N" --timeout 3 >/dev/null 2>&1 &
pid=$!
if wait_pid_exit 12 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  elapsed=$(( $(date +%s) - start ))
  if [[ "$rc" -eq 1 ]] && [[ "$elapsed" -ge 3 ]] && [[ "$elapsed" -lt 12 ]] && [[ -f "${FSW}.called" ]]; then
    ok "超时包裹：真调 fswatch 永挂 + timeout 3 → bash kill → exit 1 (${elapsed}s)"
  else
    bad "timeout-wrap: rc=$rc elapsed=${elapsed}s called=$([[ -f "${FSW}.called" ]]&&echo y||echo n) (want rc=1,3<=t<12,called=y)"
  fi
else
  kill "$pid" 2>/dev/null; bad "timeout-wrap: never exited (永挂未被 kill → 超时包裹失效)"
fi

# ═══ v1.38: startup gate — 防止 wait-marker 等一个没提交的任务 ═══
echo ""
echo "§v1.38 startup gate（IDLE/residual fail-fast）"

STUBTMUX_DIR=$(mktemp -d "/tmp/cc-wm-tmux.XXXXXX")
make_tmux_stub() { # <mode: idle|residual|queue|running>
  local mode="$1"
  local p="$STUBTMUX_DIR/tmux-$mode.sh"
  cat > "$p" <<'STUB'
#!/usr/bin/env bash
mode="$CC_WAIT_TMUX_MODE"
log="$CC_WAIT_TMUX_LOG"
case "${1:-}" in
  capture-pane)
    case "$mode" in
      idle)     printf '────────────────\n❯ \n────────────────\n  ⏵⏵ bypass permissions on\n' ;;
      residual) printf '────────────────\n❯ 按 /tmp/cc-task.md 执行\n────────────────\n  ⏵⏵ bypass permissions on\n' ;;
      residual_write) printf '────────────────\n❯ Write tests per /tmp/cc-task.md\n────────────────\n  ⏵⏵ bypass permissions on\n' ;;
      old_tool_idle) printf '⏺ Write file done earlier\n────────────────\n❯ \n────────────────\n  ⏵⏵ bypass permissions on\n' ;;
      queue)    printf 'Press up to edit queued messages\n❯ 按 /tmp/cc-task.md 执行\n' ;;
      running)  printf '✻ Thinking…\n' ;;
      *)        printf '' ;;
    esac ;;
  send-keys)
    printf '%s\n' "$*" >> "$log" ;;
  *) : ;;
esac
STUB
  chmod +x "$p"
  echo "$p"
}

# Test 16: clean IDLE + no newer marker → exit 4 immediately（不等 timeout）
rm -f "$MARKER"
TMUX_STUB=$(make_tmux_stub idle); LOG="$STUBTMUX_DIR/idle.log"
start=$(date +%s)
CC_WAIT_TMUX="$TMUX_STUB" CC_WAIT_TMUX_MODE=idle CC_WAIT_TMUX_LOG="$LOG" \
  bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >/dev/null 2>&1
rc=$?; elapsed=$(( $(date +%s) - start ))
if [[ "$rc" -eq 4 ]] && [[ "$elapsed" -lt 5 ]]; then
  ok "startup gate: clean IDLE + no marker → exit 4 fail-fast"
else
  bad "startup-idle: rc=$rc elapsed=$elapsed (want rc=4,<5s)"
fi

# Test 17: residual input 默认不自动 Enter（防误提交旧残留）
rm -f "$MARKER"
TMUX_STUB=$(make_tmux_stub residual); LOG="$STUBTMUX_DIR/residual.log"
CC_WAIT_TMUX="$TMUX_STUB" CC_WAIT_TMUX_MODE=residual CC_WAIT_TMUX_LOG="$LOG" CC_WAIT_START_GRACE=1 \
  bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >/dev/null 2>&1
rc=$?
if [[ "$rc" -eq 4 ]] && [[ ! -s "$LOG" ]]; then
  ok "startup gate: residual input → exit 4, no auto Enter by default"
else
  bad "startup-residual-default: rc=$rc log='$(cat "$LOG" 2>/dev/null | tr -d '\n')'"
fi

# Test 18: opt-in residual auto-submit → 补 Enter 一次，然后仍未启动则 exit 4
rm -f "$MARKER"
TMUX_STUB=$(make_tmux_stub residual); LOG="$STUBTMUX_DIR/residual-optin.log"
CC_WAIT_TMUX="$TMUX_STUB" CC_WAIT_TMUX_MODE=residual CC_WAIT_TMUX_LOG="$LOG" CC_WAIT_START_GRACE=1 CC_WAIT_AUTO_SUBMIT_RESIDUAL=1 \
  bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >/dev/null 2>&1
rc=$?
if [[ "$rc" -eq 4 ]] && [[ -f "$LOG" ]] && grep -q 'send-keys.*Enter' "$LOG"; then
  ok "startup gate: residual opt-in → auto Enter once, then fail-fast if still not started"
else
  bad "startup-residual-optin: rc=$rc log='$(cat "$LOG" 2>/dev/null | tr -d '\n')'"
fi

# Test 19: residual 文本含 Write/Edit/Tool 等关键词也不能误判 RUNNING
rm -f "$MARKER"
TMUX_STUB=$(make_tmux_stub residual_write); LOG="$STUBTMUX_DIR/residual-write.log"
CC_WAIT_TMUX="$TMUX_STUB" CC_WAIT_TMUX_MODE=residual_write CC_WAIT_TMUX_LOG="$LOG" \
  bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >/dev/null 2>&1
rc=$?
if [[ "$rc" -eq 4 ]] && [[ ! -s "$LOG" ]]; then
  ok "startup gate: residual containing Write → still exit 4, no RUNNING false-positive"
else
  bad "startup-residual-write: rc=$rc log='$(cat "$LOG" 2>/dev/null | tr -d '\n')'"
fi

# Test 20: prompt 上方旧 tool 输出 + 当前空 prompt → exit 4，不误判 RUNNING
rm -f "$MARKER"
TMUX_STUB=$(make_tmux_stub old_tool_idle); LOG="$STUBTMUX_DIR/old-tool-idle.log"
CC_WAIT_TMUX="$TMUX_STUB" CC_WAIT_TMUX_MODE=old_tool_idle CC_WAIT_TMUX_LOG="$LOG" \
  bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >/dev/null 2>&1
rc=$?
if [[ "$rc" -eq 4 ]]; then
  ok "startup gate: old tool scrollback + empty prompt → exit 4, no RUNNING false-positive"
else
  bad "startup-old-tool-idle: rc=$rc (want 4)"
fi

# Test 21: queued-message mode → exit 4，不补 Enter（避免继续累积队列）
rm -f "$MARKER"
TMUX_STUB=$(make_tmux_stub queue); LOG="$STUBTMUX_DIR/queue.log"
CC_WAIT_TMUX="$TMUX_STUB" CC_WAIT_TMUX_MODE=queue CC_WAIT_TMUX_LOG="$LOG" \
  bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >/dev/null 2>&1
rc=$?
if [[ "$rc" -eq 4 ]] && [[ ! -s "$LOG" ]]; then
  ok "startup gate: queued-message mode → exit 4, no auto Enter"
else
  bad "startup-queue: rc=$rc log='$(cat "$LOG" 2>/dev/null | tr -d '\n')'"
fi

# Test 22: 真 running 输出 → startup gate 放行，最终按 timeout exit 1（不是 exit 4）
rm -f "$MARKER"
TMUX_STUB=$(make_tmux_stub running); LOG="$STUBTMUX_DIR/running.log"
CC_WAIT_TMUX="$TMUX_STUB" CC_WAIT_TMUX_MODE=running CC_WAIT_TMUX_LOG="$LOG" CC_WAIT_MODE=fallback \
  bash "$SCRIPT" --session "$SESS" --after 0 --timeout 1 >/dev/null 2>&1
rc=$?
if [[ "$rc" -eq 1 ]]; then
  ok "startup gate: true running pane → gate passes, timeout path owns exit 1"
else
  bad "startup-running: rc=$rc (want 1, not 4)"
fi

rm -rf "$STUBTMUX_DIR"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
