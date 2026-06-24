#!/usr/bin/env bash
# test-gate-verify.sh — gate-verify.sh 客观验收 gate 的 TDD
# 重点覆盖 --expect-artifacts 前置硬门（exit 10，gate-danger 同语义）+ 向后兼容。

set -uo pipefail

GV="$(cd "$(dirname "$0")/../scripts/gate" && pwd)/gate-verify.sh"
TMP="/tmp/cc-gvtest-$$"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
cleanup(){ rm -rf "$TMP"; }
trap cleanup EXIT
cleanup; mkdir -p "$TMP"

echo "=== gate-verify TDD: --expect-artifacts 前置硬门 + 向后兼容 ==="
echo ""

printf 'data\n' > "$TMP/ok.md"      # 非空
printf 'more\n' > "$TMP/ok2.md"     # 非空
: > "$TMP/empty.md"                  # 0 字节
# none.md 故意不创建

run(){ bash "$GV" "$@" >/dev/null 2>&1; echo $?; }

# Test 1: 向后兼容 — 不传 --expect-artifacts，行为完全不变（artifact 存在 → 0）
rc=$(run --artifact "$TMP/ok.md")
[[ "$rc" -eq 0 ]] && ok "向后兼容：仅 --artifact 存在 → 0" || bad "向后兼容破坏 rc=$rc"

# Test 2: 向后兼容 — 仅 --cmd 成功 → 0
rc=$(run --cmd "true")
[[ "$rc" -eq 0 ]] && ok "向后兼容：仅 --cmd true → 0" || bad "cmd 路径破坏 rc=$rc"

# Test 3: expect 命中且非空 → 0
rc=$(run --expect-artifacts "$TMP/ok.md")
[[ "$rc" -eq 0 ]] && ok "expect 命中且非空 → 0" || bad "expect-pass 错误 rc=$rc"

# Test 4: expect glob 零匹配 → 10（硬门）
rc=$(run --expect-artifacts "$TMP/none*.md")
[[ "$rc" -eq 10 ]] && ok "expect glob 零匹配 → 10" || bad "零匹配应 10，得 rc=$rc"

# Test 5: expect 命中但 0 字节 → 10
rc=$(run --expect-artifacts "$TMP/empty.md")
[[ "$rc" -eq 10 ]] && ok "expect 命中但 0 字节 → 10" || bad "0 字节应 10，得 rc=$rc"

# Test 6: expect 字面路径不存在 → 10
rc=$(run --expect-artifacts "$TMP/none.md")
[[ "$rc" -eq 10 ]] && ok "expect 字面缺失 → 10" || bad "字面缺失应 10，得 rc=$rc"

# Test 7: 逗号分隔多 glob，一个缺 → 10
rc=$(run --expect-artifacts "$TMP/ok.md,$TMP/none.md")
[[ "$rc" -eq 10 ]] && ok "逗号分隔任一缺 → 10" || bad "逗号分隔应 10，得 rc=$rc"

# Test 8: 通配 glob 命中多文件且都非空 → 0
rc=$(run --expect-artifacts "$TMP/ok*.md")
[[ "$rc" -eq 0 ]] && ok "通配命中多非空文件 → 0" || bad "多命中应 0，得 rc=$rc"

# Test 9: 可多次指定 --expect-artifacts，一个缺 → 10
rc=$(run --expect-artifacts "$TMP/ok.md" --expect-artifacts "$TMP/none.md")
[[ "$rc" -eq 10 ]] && ok "多次 --expect-artifacts 任一缺 → 10" || bad "多次指定应 10，得 rc=$rc"

# Test 10: expect 前置失败时，--cmd 根本不应执行（硬门在验收之前）
SENTINEL="$TMP/cmd-ran"
rm -f "$SENTINEL"
bash "$GV" --expect-artifacts "$TMP/none.md" --cmd "touch $SENTINEL" >/dev/null 2>&1
[[ ! -f "$SENTINEL" ]] && ok "expect 失败 → cmd 不执行（前置硬门）" || bad "expect 失败后 cmd 仍执行了"

# Test 11: expect 全过 + cmd 过 → 0
rc=$(run --expect-artifacts "$TMP/ok.md" --cmd "true")
[[ "$rc" -eq 0 ]] && ok "expect 过 + cmd 过 → 0" || bad "组合应 0，得 rc=$rc"

# Test 12: 啥都不传 → 3（参数错误，与原行为一致）
rc=$(run)
[[ "$rc" -eq 3 ]] && ok "无参数 → 3" || bad "无参数应 3，得 rc=$rc"

# Test 13: --help 含新参数文档
bash "$GV" --help 2>&1 | grep -q "expect-artifacts" && ok "--help 列出 expect-artifacts" || bad "--help 缺新参数"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
