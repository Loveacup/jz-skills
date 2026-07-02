#!/bin/bash
# pdf skill 收尾漂移门 / pdf skill drift gate
#
#   full (默认)      : source 自洽 + source==canonical==4 runtime（部署后交付门）
#   --source-only    : 仅 source 自洽（无源码级 chrome hack + SKILL.md 文档同步），
#                      供 pre-commit 在未部署阶段使用，不要求 canonical 已就绪。
#
# 退出 0 = 通过；非 0 = 漂移，禁止静默收尾。
set -uo pipefail

MODE="${1:-full}"
# Resolve paths dynamically — no hardcoded $HOME (platform-agnostic + 不泄露用户名/家目录)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REAL_HOME="$(python3 -c 'import os, pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
SRC="${SRC:-$REPO_ROOT/shared/2pdf}"
CANON="${CANON:-$REAL_HOME/.agents/shared/2pdf}"
RUNTIMES=(
  "$REAL_HOME/.claude/skills/2pdf"
  "$REAL_HOME/.codex/skills/2pdf"
  "$REAL_HOME/.cursor/skills/2pdf"
  "$REAL_HOME/.hermes/skills/2pdf"
)
FILT='__pycache__|\.pytest_cache|\.pyc'
FAIL=0

echo "== PDF DRIFT GATE (${MODE}) =="

# [always] source 无源码级 chrome hack（source 是权威，绝不该有 channel:'chrome'）
if grep -rn "channel: *'chrome'" "$SRC/scripts/" >/dev/null 2>&1; then
  echo "❌ REDLINE: source 含 channel:'chrome'（应参数化为 --browser）"; FAIL=1
else
  echo "✅ source 无源码级 chrome hack"
fi

# [always] 文档同步门：脚本能力必须出现在 SKILL.md
python3 - "$SRC" <<'PY' || FAIL=1
import sys, pathlib
root = pathlib.Path(sys.argv[1])
skill = (root / "SKILL.md").read_text(encoding="utf-8")
themes = sorted(p.stem for p in (root / "scripts" / "themes").glob("*.css"))
miss_theme = [t for t in themes if t not in skill]
miss_flag = [k for k in ("--format", "--page-size", "--browser", "--preflight") if k not in skill]
miss_fmt = [f for f in ("png", "html", "wechat") if f not in skill]
problems = []
if miss_flag: problems.append(f"缺参数 {miss_flag}")
if miss_fmt: problems.append(f"缺格式 {miss_fmt}")
if miss_theme: problems.append(f"缺主题 {miss_theme}")
if problems:
    print("❌ DOC: SKILL.md 与脚本能力不一致 —", "; ".join(problems)); sys.exit(1)
print(f"✅ SKILL.md 覆盖全部参数/格式/{len(themes)} 主题")
PY

if [ "$MODE" != "--source-only" ]; then
  # [full] source vs canonical：仅允许 build 噪声差异
  if [ -d "$CANON" ]; then
    d=$(diff -rq "$SRC" "$CANON" 2>&1 | grep -vE "$FILT" || true)
    if [ -n "$d" ]; then echo "❌ source != canonical:"; echo "$d" | sed 's/^/    /'; FAIL=1
    else echo "✅ source == canonical"; fi
  else
    echo "❌ canonical 缺失: $CANON（未部署？）"; FAIL=1
  fi

  # [full] canonical 无源码级 chrome hack
  if [ -d "$CANON" ] && grep -rn "channel: *'chrome'" "$CANON/scripts/" >/dev/null 2>&1; then
    echo "❌ REDLINE: canonical 仍含 channel:'chrome'"; FAIL=1
  elif [ -d "$CANON" ]; then
    echo "✅ canonical 无源码级 chrome hack"
  fi

  # [full] 每条 runtime 软链解析到 canonical 且内容一致
  for r in "${RUNTIMES[@]}"; do
    [ -e "$r" ] || { echo "ℹ️  runtime 不存在(跳过): $r"; continue; }
    tgt=$(readlink "$r" 2>/dev/null || true)
    if [ "$tgt" != "$CANON" ]; then
      echo "❌ SYMLINK: $r -> ${tgt:-<非软链>}（应 -> $CANON）"; FAIL=1; continue
    fi
    d=$(diff -rq "$r/" "$CANON/" 2>&1 | grep -vE "$FILT" || true)
    [ -n "$d" ] && { echo "❌ DRIFT runtime $r"; FAIL=1; } || echo "✅ runtime ok: $r"
  done
fi

echo "===================="
if [ "$FAIL" -eq 0 ]; then echo "🎉 PDF DRIFT GATE PASS"; exit 0
else echo "🚨 PDF DRIFT GATE FAIL（禁止静默收尾）"; exit 1; fi
