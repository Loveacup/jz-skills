#!/usr/bin/env bash
# test-concurrency.sh — TDD for concurrent temp+mv atomic write pattern
#
# Blind spot: the temp+mv pattern prevents torn reads, but concurrent
# writers can still RMW-race. This test exercises the exact write pattern
# used by cc-monitor (heartbeat), cc-status-writer (status JSON),
# cc-topic-map (registry), cc-usage (usage JSON), and cc-watcher (grep output).
#
# Tests:
#  1. Single writer: final file = written content
#  2. 2 parallel writers: final file is one complete entry (not torn/interleaved)
#  3. 10 parallel writers: final file is valid (one complete entry, no garbage)
#  4. temp file is always cleaned up (no orphaned tmp files after race)
#  5. Reader during concurrent write never sees 0-byte result (mv is atomic)

set -euo pipefail

PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

TMP="/tmp/cc-concurrency-test-$$"
cleanup(){ rm -rf "$TMP"; }
trap cleanup EXIT
cleanup; mkdir -p "$TMP"

echo "=== concurrency TDD: temp+mv atomic write pattern ==="
echo ""

# ── atomic_write(): the exact pattern used by cc-monitor et al. ──
atomic_write() {
  local target="$1" content="$2"
  local tmpf; tmpf=$(mktemp "$target.XXXXXX")
  printf '%s\n' "$content" > "$tmpf"
  mv "$tmpf" "$target"
}

# ── Test 1: single writer — baseline ──
F1="$TMP/single.txt"
atomic_write "$F1" "hello world"
if [[ "$(cat "$F1")" == "hello world" ]]; then
  ok "单写: 内容完整一致"
else
  bad "单写: 内容不匹配"
fi

# ── Test 2: 2 parallel writers — no torn writes ──
F2="$TMP/dual.txt"
(
  for i in $(seq 1 50); do
    atomic_write "$F2" "writer-A-iteration-$i"
  done
) &
PID_A=$!
(
  for i in $(seq 1 50); do
    atomic_write "$F2" "writer-B-iteration-$i"
  done
) &
PID_B=$!
wait $PID_A $PID_B

content=$(cat "$F2")
if [[ "$content" =~ ^writer-[AB]-iteration-[0-9]+$ ]]; then
  ok "2并发写: 文件内容完整(未撕裂)"
else
  bad "2并发写: 文件损坏: ${content:0:80}"
fi

# ── Test 3: 10 parallel writers — stress ──
F3="$TMP/many.txt"
pids=()
for w in $(seq 0 9); do
  (
    for i in $(seq 1 20); do
      atomic_write "$F3" "writer-$w-iter-$i"
      # tiny sleep to increase interleaving
    done
  ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done

content=$(cat "$F3")
if [[ "$content" =~ ^writer-[0-9]-iter-[0-9]+$ ]]; then
  ok "10并发写: 文件未损坏"
else
  bad "10并发写: 文件异常: ${content:0:80}"
fi

# ── Test 4: no orphaned temp files ──
F4="$TMP/orphan.txt"
before=$(find "$TMP" -name 'orphan.txt.*' 2>/dev/null | wc -l | tr -d ' ')
pids=()
for w in $(seq 0 4); do
  (
    for i in $(seq 1 30); do
      atomic_write "$F4" "data-$w-$i"
    done
  ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
after=$(find "$TMP" -name 'orphan.txt.*' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$after" -eq 0 ]]; then
  ok "无孤儿 temp 文件: 并发后无残留"
else
  bad "孤儿 temp 文件: 残留 $after 个"
fi

# ── Test 5: mv atomicity — reader never sees 0-byte ──
F5="$TMP/atomic.txt"
echo "initial" > "$F5"
saw_zero=0
(
  for i in $(seq 1 200); do
    atomic_write "$F5" "round-$i-data-here-more-bytes-to-avoid-empty"
  done
) &
WRITER=$!
# Reader: check file size during concurrent writes
for i in $(seq 1 100); do
  sz=$(wc -c < "$F5" 2>/dev/null || echo 0)
  if [[ "$sz" -eq 0 ]]; then
    saw_zero=1
    break
  fi
done
wait $WRITER
if [[ "$saw_zero" -eq 0 ]]; then
  ok "mv 原子性: reader 从未看到 0 字节文件"
else
  bad "mv 原子性: reader 看到了 0 字节文件 (mv 非原子!)"
fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
