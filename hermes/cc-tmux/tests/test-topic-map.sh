#!/usr/bin/env bash
# test-topic-map.sh — TDD for R9b Topic↔Session 会话复用 (cc-topic-map.sh + cc-start --topic)
#
# HERMETIC: CC_TOPIC_MAP_FILE injects the registry path; CC_TOPIC_TMUX injects a stub tmux
# (same pattern as cc-gc's CC_GC_TMUX). cc-start --topic reuse path tested end-to-end via stub;
# new-build path tested via full stub (new-session stub succeeds → asserts map unset+set).

set -uo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
MAPSH="$DIR/scripts/cc-topic-map.sh"
STARTSH="$DIR/scripts/cc-start.sh"
PASS=0 FAIL=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

D=""; MAP=""; STUB=""
new_sandbox(){
  D=$(mktemp -d "/tmp/cc-topic-test.XXXXXX")
  MAP="$D/cc-topic-map.json"
  mkdir -p "$D/alive" "$D/pane"; : > "$D/sessions.txt"
  STUB="$D/stub-tmux.sh"
  cat > "$STUB" <<'STUB'
#!/usr/bin/env bash
D="$CC_TOPIC_STUB_DIR"; cmd="${1:-}"; shift || true
name=""; args=("$@")
for ((i=0;i<${#args[@]};i++)); do [[ "${args[i]}" == "-t" ]] && name="${args[i+1]:-}"; done
case "$cmd" in
  list-sessions)   cat "$D/sessions.txt" 2>/dev/null ;;
  has-session)     [[ -f "$D/alive/$name" ]] && exit 0 || exit 1 ;;
  capture-pane)    cat "$D/pane/$name.txt" 2>/dev/null ;;
  new-session)     exit 0 ;;
  send-keys)       exit 0 ;;
  display-message) echo 12345 ;;
  kill-session)    exit 0 ;;
  *) exit 0 ;;
esac
STUB
  chmod +x "$STUB"
}
cleanup_all(){ [[ -n "$D" && -d "$D" ]] && rm -rf "$D"; }
trap cleanup_all EXIT

m(){ CC_TOPIC_MAP_FILE="$MAP" CC_TOPIC_TMUX="bash $STUB" CC_TOPIC_STUB_DIR="$D" bash "$MAPSH" "$@"; }

echo "=== cc-topic-map TDD: R9b Topic↔Session 会话复用 ==="
echo ""

# ── TC1: get 不存在 key → 空 ──
new_sandbox
out=$(m get 99999 2>/dev/null || true)
[[ -z "$out" ]] && ok "TC1 get 不存在 key → 空" || bad "TC1 got '$out'"
cleanup_all

# ── TC2: set + get → 返回正确 session ──
new_sandbox
m set 56082 "hermes-cc-default-jz-skills-0622-1217" >/dev/null 2>&1
out=$(m get 56082 2>/dev/null || true)
[[ "$out" == "hermes-cc-default-jz-skills-0622-1217" ]] && ok "TC2 set + get → 正确 session" || bad "TC2 got '$out'"
cleanup_all

# ── TC3: unset → get 返回空 ──
new_sandbox
m set 56082 "sess-A" >/dev/null 2>&1; m unset 56082 >/dev/null 2>&1
out=$(m get 56082 2>/dev/null || true)
[[ -z "$out" ]] && ok "TC3 unset → get 空" || bad "TC3 got '$out'"
cleanup_all

# ── TC4: cleanup → 死 session 清、活 session 留 ──
new_sandbox
m set 100 "live-sess" >/dev/null 2>&1; m set 200 "dead-sess" >/dev/null 2>&1
: > "$D/alive/live-sess"   # live-sess 存活；dead-sess 不存活
m cleanup >/dev/null 2>&1
live=$(m get 100 2>/dev/null || true); dead=$(m get 200 2>/dev/null || true)
if [[ "$live" == "live-sess" && -z "$dead" ]]; then ok "TC4 cleanup → 死清活留"; else bad "TC4 live='$live' dead='$dead'"; fi
cleanup_all

# ── TC5: list → 正确列出 ──
new_sandbox
m set 100 "sess-X" >/dev/null 2>&1; m set 200 "sess-Y" >/dev/null 2>&1
out=$(m list 2>/dev/null || true)
if grep -q 'sess-X' <<<"$out" && grep -q 'sess-Y' <<<"$out" && grep -q '100' <<<"$out"; then ok "TC5 list → 正确列出"; else bad "TC5 out='$(tr '\n' '|' <<<"$out")'"; fi
cleanup_all

# ── TC6: unset-by-session → 按 session 反查删（cc-finish --clean-topic-map 用） ──
new_sandbox
m set 100 "sess-keep" >/dev/null 2>&1; m set 200 "sess-kill" >/dev/null 2>&1
m unset-by-session "sess-kill" >/dev/null 2>&1
keep=$(m get 100 2>/dev/null || true); killed=$(m get 200 2>/dev/null || true)
if [[ "$keep" == "sess-keep" && -z "$killed" ]]; then ok "TC6 unset-by-session → 反查删对应条目"; else bad "TC6 keep='$keep' killed='$killed'"; fi
cleanup_all

# ── helper: 跑 cc-start（注入 stub tmux + map + skill root） ──
start(){ CC_TOPIC_MAP_FILE="$MAP" CC_TOPIC_TMUX="bash $STUB" CC_TOPIC_STUB_DIR="$D" \
         CC_TMUX_SKILL_ROOT="$DIR" bash "$STARTSH" "$@" 2>"$D/start.err"; }

# ── TC7: cc-start --topic 复用路径（stub: session 存活 + IDLE + 心跳新鲜）──
new_sandbox
RS="hermes-cc-default-reuse-0101-0000"
m set 70001 "$RS" >/dev/null 2>&1
: > "$D/alive/$RS"; printf '❯ \n' > "$D/pane/$RS.txt"      # 存活 + IDLE pane
touch "/tmp/cc-heartbeat-$RS"                              # 心跳新鲜（now）
T="topicreuse-$$"
out=$(start --target "$T" --task x --topic 70001 || true)
rm -f "/tmp/cc-heartbeat-$RS"; rm -rf "/tmp/cc-lock-$T"
if [[ "$out" == "$RS" ]]; then ok "TC7 cc-start --topic 复用：输出复用 session，不新建"; else bad "TC7 out='$out' err='$(tail -1 "$D/start.err" 2>/dev/null)'"; fi
cleanup_all

# ── TC8: cc-start --topic 新建路径（stub: 映射 session 已死）→ unset 旧 + set 新 ──
new_sandbox
DS="hermes-cc-default-dead-0101-0000"
m set 80001 "$DS" >/dev/null 2>&1                          # 映射指向死 session（不在 alive/）
T="topicnew-$$"
out=$(start --target "$T" --task x --topic 80001 || true)
newmap=$(m get 80001 2>/dev/null || true)
rm -rf "/tmp/cc-lock-$T" "/tmp/cc-watch-$out.log" 2>/dev/null
if [[ -n "$out" && "$out" != "$DS" && "$newmap" == "$out" ]]; then ok "TC8 cc-start --topic 新建：死 session→unset 旧+set 新映射"; else bad "TC8 out='$out' newmap='$newmap' dead='$DS' err='$(tail -1 "$D/start.err" 2>/dev/null)'"; fi
cleanup_all

# ── TC9: cc-start 无 --topic → 原行为不变（不碰 map，零回归）──
new_sandbox
echo '{}' > "$MAP"
T="topicnone-$$"
out=$(start --target "$T" --task x || true)
mapcontent=$(cat "$MAP" 2>/dev/null)
rm -rf "/tmp/cc-lock-$T" "/tmp/cc-watch-$out.log" 2>/dev/null
if [[ -n "$out" && "$mapcontent" == "{}" ]]; then ok "TC9 无 --topic → 不碰 map（零回归）"; else bad "TC9 out='$out' map='$mapcontent'"; fi
cleanup_all

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
