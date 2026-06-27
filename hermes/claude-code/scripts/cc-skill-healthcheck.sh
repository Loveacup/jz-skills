#!/bin/bash
# cc-skill-healthcheck.sh — claude-code skill 结构健康检查 / structural healthcheck
#
# 用途：在修改 claude-code skill 后跑此脚本，确保源↔运行端一致、无结构缺陷。
# Purpose: run after editing the claude-code skill to gate source↔runtime consistency
#          and catch structural defects. 8 hard checks (T1-T7) + 1 manual gate (T8).
#
# Usage:  bash hermes/claude-code/scripts/cc-skill-healthcheck.sh
# Exit:   0 = all T1-T7 pass · 1 = at least one failed (T8 is a manual gate, never fails build)
#
# 设计为 fail-loud：每项打印 PASS/FAIL 与证据，结尾汇总。CQI TDD baseline 用。

set -uo pipefail

# 字面绝对路径，不用 $HOME：Hermes profile 把 $HOME override 到 profiles/<name>/home/，
# 用 $HOME 会指向 regent/home 等错误位置（见 references/common-pitfalls.md #2）。
SRC_DIR="/Users/alexcai/code/jz-skills/hermes/claude-code"
RT_DIR="/Users/alexcai/.hermes/skills/autonomous-ai-agents/claude-code"
SRC_SKILL="$SRC_DIR/SKILL.md"
RT_SKILL="$RT_DIR/SKILL.md"

THRESHOLD_LINES=450                       # DP4 salience target
RETIRED_NUMS="16 17 29 32 34 35"          # 历史合并/废弃编号，永不重用 (SKILL.md 编号纪律)

PASS=0
FAIL=0

md5q() { md5 -q "$1" 2>/dev/null || md5sum "$1" 2>/dev/null | awk '{print $1}'; }
ok()   { echo "  ✅ PASS  $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ FAIL  $1"; FAIL=$((FAIL+1)); }

echo "════════════════════════════════════════════════════════════"
echo " claude-code skill healthcheck"
echo "   source : $SRC_SKILL"
echo "   runtime: $RT_SKILL"
echo "════════════════════════════════════════════════════════════"

# ── T1: source/runtime SKILL.md md5 一致 ──────────────────────────
echo "── T1  SKILL.md md5 consistency (source == runtime)"
if [ -f "$SRC_SKILL" ] && [ -f "$RT_SKILL" ]; then
  s=$(md5q "$SRC_SKILL"); r=$(md5q "$RT_SKILL")
  if [ "$s" = "$r" ]; then ok "md5 match ($s)"
  else bad "md5 differ — source=$s runtime=$r"; fi
else
  bad "SKILL.md missing (source or runtime)"
fi

# ── T2: source SKILL.md 行数 <= 阈值 (salience) ───────────────────
echo "── T2  SKILL.md line count <= $THRESHOLD_LINES (salience)"
if [ -f "$SRC_SKILL" ]; then
  n=$(wc -l < "$SRC_SKILL" | tr -d ' ')
  if [ "$n" -le "$THRESHOLD_LINES" ]; then ok "$n lines (<= $THRESHOLD_LINES)"
  else bad "$n lines (> $THRESHOLD_LINES)"; fi
else
  bad "source SKILL.md missing"
fi

# ── T3: pitfall 编号无重复 + 不重用废弃号 ─────────────────────────
echo "── T3  pitfall numbering: no duplicate, no reuse of retired ($RETIRED_NUMS)"
if [ -f "$SRC_SKILL" ]; then
  nums=$(grep -oE '^\| *★?[0-9]+ *\|' "$SRC_SKILL" | grep -oE '[0-9]+')
  dups=$(echo "$nums" | sort -n | uniq -d)
  reused=""
  for rt in $RETIRED_NUMS; do
    if echo "$nums" | grep -qx "$rt"; then reused="$reused $rt"; fi
  done
  if [ -z "$dups" ] && [ -z "$reused" ]; then
    ok "$(echo "$nums" | sort -nu | wc -l | tr -d ' ') unique pitfalls, no dup, no retired-reuse"
  else
    [ -n "$dups" ]   && bad "duplicate pitfall #: $(echo $dups | tr '\n' ' ')"
    [ -n "$reused" ] && bad "reused retired #:$reused"
  fi
else
  bad "source SKILL.md missing"
fi

# ── T4: dead references — SKILL.md 提到的 references/*.md 必须存在 ──
echo "── T4  no dead references (every references/*.md cited exists)"
if [ -f "$SRC_SKILL" ]; then
  missing=""
  for ref in $(grep -oE 'references/[A-Za-z0-9._-]+\.md' "$SRC_SKILL" | sort -u); do
    [ -f "$SRC_DIR/$ref" ] || missing="$missing $ref"
  done
  if [ -z "$missing" ]; then ok "all cited references exist"
  else bad "dead reference(s):$missing"; fi
else
  bad "source SKILL.md missing"
fi

# ── T5: reference 文件集合 source == runtime ─────────────────────
echo "── T5  reference file-set consistency (source == runtime)"
if [ -d "$SRC_DIR/references" ] && [ -d "$RT_DIR/references" ]; then
  d=$(diff <(cd "$SRC_DIR/references" && ls -1 | sort) <(cd "$RT_DIR/references" && ls -1 | sort))
  if [ -z "$d" ]; then ok "identical file set ($(ls -1 "$SRC_DIR/references" | wc -l | tr -d ' ') files)"
  else bad "file-set differs:"; echo "$d" | sed 's/^/        /'; fi
else
  bad "references/ dir missing (source or runtime)"
fi

# ── T6: 同名 reference 内容 md5 一致 ─────────────────────────────
echo "── T6  same-name reference content md5 consistency"
if [ -d "$SRC_DIR/references" ] && [ -d "$RT_DIR/references" ]; then
  forks=""
  for f in "$SRC_DIR/references"/*.md; do
    base=$(basename "$f")
    rt="$RT_DIR/references/$base"
    [ -f "$rt" ] || continue
    [ "$(md5q "$f")" = "$(md5q "$rt")" ] || forks="$forks $base"
  done
  if [ -z "$forks" ]; then ok "all common references identical"
  else bad "content fork(s):$forks"; fi
else
  bad "references/ dir missing (source or runtime)"
fi

# ── T7: 关键 canonical 段落存在 ──────────────────────────────────
echo "── T7  canonical sections present in source SKILL.md"
if [ -f "$SRC_SKILL" ]; then
  t7fail=0
  check7() { if grep -q "$1" "$SRC_SKILL"; then echo "        ✓ $2"; else echo "        ✗ $2"; t7fail=1; fi; }
  check7 'manual-patrol-after-report' 'patrol canonical (manual-patrol-after-report)'
  check7 'Final Input-Line Gate'      'final input-line gate'
  check7 'tmux-bridge'                'tmux-bridge pilot/fallback'
  check7 'drift-check.sh'             'fail-open drift hook (drift-check.sh)'
  if [ "$t7fail" -eq 0 ]; then ok "all 4 canonical sections present"
  else bad "missing canonical section(s) — see ✗ above"; fi
else
  bad "source SKILL.md missing"
fi

# ── T8: behavior validation (manual gate, never fails build) ─────
echo "── T8  behavior validation (MANUAL GATE — not automatable)"
echo "  ⏳ PENDING  须在下一个 >=10min 真实任务中验证：3 轮真实 patrol (capture→📡 配对) +"
echo "             收尾 Final Input-Line Gate 实际执行。记录于 CQI 文档，本脚本不判定。"

echo "════════════════════════════════════════════════════════════"
echo " RESULT: $PASS passed, $FAIL failed  (T8 manual gate pending)"
echo "════════════════════════════════════════════════════════════"
[ "$FAIL" -eq 0 ]
