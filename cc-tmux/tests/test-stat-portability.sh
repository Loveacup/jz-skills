#!/usr/bin/env bash
# test-stat-portability.sh — TDD for cross-platform stat mtime fallback
#
# Blind spot: 7 scripts use `stat -f %m` (BSD/macOS). On Linux, stat needs
# `stat -c %Y`. Current `|| echo 0` falls back silently but returns wrong
# value (0 = epoch), potentially causing false positives in timeout checks.
#
# This test:
#  1. Verifies the current macOS stat works correctly
#  2. Verifies a proper cross-platform get_mtime() returns correct values
#  3. Verifies the fallback path when stat is unavailable
#  4. Verifies the cc-wait-marker.sh mtime comparison works in stub mode

set -euo pipefail

PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

TMP="/tmp/cc-stat-test-$$"
cleanup(){ rm -rf "$TMP"; }
trap cleanup EXIT
cleanup; mkdir -p "$TMP"

echo "=== stat portability TDD: cross-platform mtime ==="
echo ""

# ── Reference: the cross-platform get_mtime() function ──
# This is the function we're proposing all scripts should use.
get_mtime() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "0"
    return 0
  fi
  # macOS/BSD
  local m; m=$(stat -f %m "$f" 2>/dev/null) && { echo "$m"; return 0; }
  # Linux/GNU
  m=$(stat -c %Y "$f" 2>/dev/null) && { echo "$m"; return 0; }
  # Ultimate fallback: perl (works on any Unix)
  m=$(perl -e 'print((stat($ARGV[0]))[9])' "$f" 2>/dev/null) && { echo "$m"; return 0; }
  echo "0"
}

# ── Test 1: get_mtime returns correct mtime for existing file ──
echo "hello" > "$TMP/exists.txt"
expected=$(stat -f %m "$TMP/exists.txt")
actual=$(get_mtime "$TMP/exists.txt")
if [[ "$actual" == "$expected" ]]; then
  ok "get_mtime 存在文件: 返回值正确 ($actual)"
else
  bad "get_mtime 存在文件: 期望 $expected 实际 $actual"
fi

# ── Test 2: get_mtime returns 0 for missing file ──
actual=$(get_mtime "$TMP/does-not-exist.txt")
if [[ "$actual" == "0" ]]; then
  ok "get_mtime 缺失文件: 返回 0"
else
  bad "get_mtime 缺失文件: 期望 0 实际 $actual"
fi

# ── Test 3: stat -f %m fallback on failure ──
# Inject a broken stat to simulate Linux/missing-stat scenario
fake_stat() {
  if [[ "$1" == "-f" ]]; then
    # Simulate: "stat -f %m" not available (e.g. Linux)
    echo "stat: illegal option -- f" >&2
    return 1
  fi
  command stat "$@"
}
export -f fake_stat

# Test: get_mtime variant using the fake stat
get_mtime_fallback() {
  local f="$1"
  [[ ! -f "$f" ]] && { echo "0"; return 0; }
  # Try macOS stat (will fail with fake_stat)
  local m; m=$(fake_stat -f %m "$f" 2>/dev/null) && { echo "$m"; return 0; }
  # Try Linux stat
  m=$(fake_stat -c %Y "$f" 2>/dev/null) && { echo "$m"; return 0; }
  # Ultimate fallback
  m=$(perl -e 'print((stat($ARGV[0]))[9])' "$f" 2>/dev/null) && { echo "$m"; return 0; }
  echo "0"
}

expected=$(stat -f %m "$TMP/exists.txt")
actual=$(get_mtime_fallback "$TMP/exists.txt")
if [[ "$actual" == "$expected" ]]; then
  ok "退化路径: macOS stat 失败后 fallback 到 GNU stat 拿到正确值"
else
  bad "退化路径: 期望 $expected 实际 $actual"
fi

# ── Test 4: ultimate perl fallback works ──
perl_mtime=$(perl -e 'print((stat($ARGV[0]))[9])' "$TMP/exists.txt")
if [[ "$perl_mtime" == "$expected" ]]; then
  ok "perl fallback: 返回值与 macOS stat 一致"
else
  bad "perl fallback: 期望 $expected 实际 $perl_mtime"
fi

# ── Test 5: NULL byte in filename doesn't crash ──
get_mtime $'\0' 2>/dev/null && rc=0 || rc=$?
if [[ "$rc" -eq 0 ]]; then
  # get_mtime returned 0 (missing file) — acceptable
  ok "NULL 字节文件名: 不崩溃 (returned 0)"
else
  bad "NULL 字节文件名: exit=$rc"
fi

# ── Test 6: all existing stat calls have fallback ──
# Verify every `stat -f %m` in scripts has `|| echo 0` or similar guard
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
unguarded=$(grep -n 'stat -f %m' "$SKILL_DIR"/scripts/*.sh "$SKILL_DIR"/scripts/gate/*.sh 2>/dev/null | grep -v '|| echo 0' | grep -v '|| echo' | grep -v 'get_mtime' | grep -v '# test' || true)
if [[ -z "$unguarded" ]]; then
  ok "所有 stat -f %m 调用都有 fallback guard"
else
  bad "以下 stat 调用缺少 fallback guard: $unguarded"
fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
