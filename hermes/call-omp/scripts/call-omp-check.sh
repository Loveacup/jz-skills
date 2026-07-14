#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# call-omp-check.sh —— 平台发现自检（manifest discovery check）
#
# 校验主文档、Markdown 引用与三份平台清单（Codex / Claude Code / OMP 自调）。
#   - 三份都在且可解析 + 都引用冒烟脚本 → 退出 0；
#   - 任一缺失 / 非法 JSON / 未引用冒烟脚本 → 非零。
#
# 【不安装、不写全局】纯本地文件校验：不改 PATH、不写任何平台全局配置、不烧 token。
#
# 用法： bash scripts/call-omp-check.sh
# 退出码： 0 三份清单齐全且合法且引用冒烟脚本 · 1 有清单缺失/非法/未引用冒烟脚本
# ─────────────────────────────────────────────────────────────────
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SMOKE_REF="scripts/call-omp-smoke.sh"

# 平台 → 清单相对路径
MANIFESTS=(
  "codex:.codex-plugin/plugin.json"
  "claude-code:.claude-plugin/plugin.json"
  "omp-self:.omp-plugin/plugin.json"
)

rc=0
SKILL_VERSION=$(awk -F': *' '/^version:/ {print $2; exit}' "$ROOT/SKILL.md")
SKILL_LINES=$(wc -l < "$ROOT/SKILL.md" | tr -d ' ')
if [[ -z "$SKILL_VERSION" ]]; then echo "❌ SKILL.md 缺 version"; rc=1; fi
if [[ "$SKILL_LINES" -gt 300 ]]; then echo "❌ SKILL.md ${SKILL_LINES} 行（须 ≤300）"; rc=1; else echo "✅ SKILL.md ${SKILL_LINES} 行"; fi
for entry in "${MANIFESTS[@]}"; do
  platform="${entry%%:*}"
  rel="${entry#*:}"
  path="$ROOT/$rel"

  if [[ ! -f "$path" ]]; then
    echo "❌ [$platform] 清单缺失: $rel"
    rc=1
    continue
  fi

  if ! jq -e . "$path" >/dev/null 2>&1; then
    echo "❌ [$platform] 非法 JSON: $rel"
    rc=1
    continue
  fi

  if ! grep -q "$SMOKE_REF" "$path"; then
    echo "❌ [$platform] 清单未引用冒烟脚本 $SMOKE_REF: $rel"
    rc=1
    continue
  fi

  manifest_version=$(jq -r '.version // ""' "$path")
  if [[ "$manifest_version" != "$SKILL_VERSION" ]]; then
    echo "❌ [$platform] version=$manifest_version，与 SKILL.md $SKILL_VERSION 不一致"
    rc=1
    continue
  fi

  echo "✅ [$platform] $rel 齐全 · version=$manifest_version · 引用 $SMOKE_REF"
done

if ! python3 - "$ROOT" <<'PY'
from pathlib import Path
import re, sys
root = Path(sys.argv[1])
broken = []
for doc in [root / 'SKILL.md', root / 'references' / 'INDEX.md']:
    text = doc.read_text()
    for target in re.findall(r'\]\(([^)]+\.md)(?:#[^)]+)?\)', text):
        if not (doc.parent / target).resolve().is_file():
            broken.append(f'{doc.relative_to(root)} -> {target}')
if broken:
    print('❌ Markdown 断链: ' + '; '.join(broken))
    raise SystemExit(1)
print('✅ SKILL.md / references/INDEX.md Markdown 链接完整')
PY
then
  rc=1
fi

if [[ $rc -eq 0 ]]; then
  echo "── 三份平台清单全部就位，call-omp 可被 Codex / Claude Code / OMP 自调发现。"
else
  echo "── 平台发现自检未通过（见上）。"
fi
exit $rc
