#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# call-omp-check.sh —— 平台发现自检（manifest discovery check）
#
# 校验三份平台清单（Codex / Claude Code / OMP 自调）齐全、是合法 JSON，
# 且各自都引用了 mock-only 冒烟入口 `scripts/call-omp-smoke.sh`。
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

  echo "✅ [$platform] $rel 齐全 · 合法 JSON · 引用 $SMOKE_REF"
done

if [[ $rc -eq 0 ]]; then
  echo "── 三份平台清单全部就位，call-omp 可被 Codex / Claude Code / OMP 自调发现。"
else
  echo "── 平台发现自检未通过（见上）。"
fi
exit $rc
